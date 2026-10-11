import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core import database
from app.models.enums import JobStatus, CertificateStatus
from app.models.job import CertificateJob, RecipientCertificate
from app.schemas.certificate import CertificateJobCreate
from app.services.generator import CertificateGenerator
from app.services.storage import StorageService

logger = logging.getLogger("bulk_certificate_generator.job_service")


class JobService:
    @staticmethod
    def create_job(db: Session, payload: CertificateJobCreate) -> CertificateJob:
        if len(payload.recipients) > settings.MAX_RECIPIENTS_PER_BATCH:
            raise ValueError(
                f"Batch size of {len(payload.recipients)} exceeds maximum allowed limit of {settings.MAX_RECIPIENTS_PER_BATCH}."
            )

        effective_issue_date = payload.issue_date or datetime.now(timezone.utc).strftime("%B %d, %Y")

        job = CertificateJob(
            event_name=payload.event_name,
            issue_date=effective_issue_date,
            issuer_name=payload.issuer_name,
            certificate_title=payload.certificate_title or "Certificate of Completion",
            description=payload.description,
            status=JobStatus.PENDING,
            total_recipients=len(payload.recipients),
            processed_recipients=0,
            successful_count=0,
            failed_count=0,
        )
        db.add(job)
        db.flush()

        now_year = datetime.now(timezone.utc).strftime("%Y")
        job_prefix = job.id[:8].upper()

        for idx, recipient in enumerate(payload.recipients, start=1):
            cert_number = f"CERT-{now_year}-{job_prefix}-{idx:04d}"
            custom_attr_str = json.dumps(recipient.custom_attributes) if recipient.custom_attributes else None

            cert = RecipientCertificate(
                job_id=job.id,
                recipient_name=recipient.name,
                recipient_email=recipient.email,
                recipient_identifier=recipient.identifier,
                custom_attributes=custom_attr_str,
                certificate_number=cert_number,
                status=CertificateStatus.PENDING,
            )
            db.add(cert)

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def process_job_background(cls, job_id: str) -> None:
        db = database.SessionLocal()
        try:
            job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
            if not job:
                logger.error("Job %s not found for background processing", job_id)
                return

            job.status = JobStatus.PROCESSING
            db.commit()

            certificates: List[RecipientCertificate] = (
                db.query(RecipientCertificate)
                .filter(RecipientCertificate.job_id == job_id)
                .order_by(RecipientCertificate.created_at.asc())
                .all()
            )

            successful_entries: List[Tuple[str, str, Path]] = []

            for cert in certificates:
                cert.status = CertificateStatus.GENERATING
                db.commit()

                try:
                    output_path = StorageService.get_certificate_path(job.id, cert.id)
                    custom_attrs = json.loads(cert.custom_attributes) if cert.custom_attributes else None

                    if cert.recipient_name == "__FORCE_FAIL__":
                        raise RuntimeError("Simulated recipient-level processing failure for fault tolerance test.")

                    CertificateGenerator.generate_pdf(
                        output_path=output_path,
                        recipient_name=cert.recipient_name,
                        event_name=job.event_name,
                        issue_date=job.issue_date,
                        issuer_name=job.issuer_name,
                        certificate_title=job.certificate_title,
                        description=job.description,
                        certificate_number=cert.certificate_number,
                        recipient_identifier=cert.recipient_identifier,
                        custom_attributes=custom_attrs,
                    )

                    cert.status = CertificateStatus.COMPLETED
                    cert.file_path = str(output_path)
                    cert.generated_at = datetime.now(timezone.utc)
                    cert.error_message = None
                    job.successful_count += 1
                    successful_entries.append((cert.recipient_name, cert.certificate_number, output_path))

                except Exception as exc:
                    logger.warning(
                        "Certificate generation failed for recipient %s (ID: %s): %s",
                        cert.recipient_name,
                        cert.id,
                        str(exc),
                    )
                    cert.status = CertificateStatus.FAILED
                    cert.error_message = str(exc)
                    job.failed_count += 1

                finally:
                    job.processed_recipients += 1
                    db.commit()

            job.completed_at = datetime.now(timezone.utc)
            if job.successful_count == job.total_recipients:
                job.status = JobStatus.COMPLETED
            elif job.successful_count > 0:
                job.status = JobStatus.PARTIALLY_FAILED
            else:
                job.status = JobStatus.FAILED

            if successful_entries:
                zip_path = StorageService.create_job_zip(job.id, successful_entries)
                if zip_path:
                    job.zip_file_path = str(zip_path)

            db.commit()
            logger.info(
                "Job %s completed with status %s (Total: %d, Succeeded: %d, Failed: %d)",
                job.id,
                job.status.value,
                job.total_recipients,
                job.successful_count,
                job.failed_count,
            )

        except Exception as exc:
            logger.exception("Catastrophic error in background job %s: %s", job_id, str(exc))
            try:
                job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
