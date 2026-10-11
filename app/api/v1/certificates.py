"""API endpoints for bulk certificate generation, status tracking, and file downloads."""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import JobStatus, CertificateStatus
from app.models.job import CertificateJob, RecipientCertificate
from app.schemas.certificate import (
    CertificateJobCreate,
    CertificateJobResponse,
    JobCreateAcceptedResponse,
    CertificateJobSummary,
    RecipientCertificateResponse,
)
from app.services.job_service import JobService
from app.services.storage import StorageService

router = APIRouter(prefix="", tags=["Certificates"])


def _build_status_url(request: Request, job_id: str) -> str:
    """Construct absolute or root-relative URL for job status polling."""
    return f"{request.base_url}api/v1/jobs/{job_id}"


def _build_download_url(request: Request, certificate_id: str) -> str:
    """Construct URL for downloading an individual certificate."""
    return f"{request.base_url}api/v1/certificates/{certificate_id}/download"


def _build_download_all_url(request: Request, job_id: str) -> str:
    """Construct URL for downloading all certificates as a ZIP archive."""
    return f"{request.base_url}api/v1/jobs/{job_id}/download-all"


@router.post(
    "/jobs",
    response_model=JobCreateAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit bulk certificate generation request",
    description=(
        "Accepts certificate metadata and a list of recipients. Validates the submission, "
        "persists the job in PENDING state, queues generation as a background task, "
        "and immediately returns HTTP 202 with a tracking URL."
    ),
)
def create_certificate_job(
    payload: CertificateJobCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> JobCreateAcceptedResponse:
    """Create a bulk generation job and queue background worker."""
    try:
        job = JobService.create_job(db=db, payload=payload)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    background_tasks.add_task(JobService.process_job_background, job.id)

    status_url = _build_status_url(request, job.id)

    return JobCreateAcceptedResponse(
        job_id=job.id,
        status=job.status,
        message="Certificate generation request accepted. Generation is executing in the background.",
        total_recipients=job.total_recipients,
        status_url=status_url,
        created_at=job.created_at,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=CertificateJobResponse,
    summary="Get job status, progress, and recipient details",
    description="Check the current status and progress of a certificate generation job.",
)
def get_job_status(
    job_id: str,
    request: Request,
    include_recipients: bool = Query(True, description="Whether to include recipient certificate items"),
    db: Session = Depends(get_db),
) -> CertificateJobResponse:
    """Retrieve the status and results of a bulk generation job."""
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate job with ID '{job_id}' not found.",
        )

    recipient_responses: List[RecipientCertificateResponse] = []
    if include_recipients:
        for cert in job.certificates:
            download_url = (
                _build_download_url(request, cert.id)
                if cert.status == CertificateStatus.COMPLETED
                else None
            )
            recipient_responses.append(
                RecipientCertificateResponse(
                    id=cert.id,
                    job_id=cert.job_id,
                    recipient_name=cert.recipient_name,
                    recipient_email=cert.recipient_email,
                    recipient_identifier=cert.recipient_identifier,
                    certificate_number=cert.certificate_number,
                    status=cert.status,
                    error_message=cert.error_message,
                    download_url=download_url,
                    created_at=cert.created_at,
                    generated_at=cert.generated_at,
                )
            )

    download_all_url = (
        _build_download_all_url(request, job.id)
        if job.successful_count > 0 and job.status in (JobStatus.COMPLETED, JobStatus.PARTIALLY_FAILED)
        else None
    )

    return CertificateJobResponse(
        id=job.id,
        event_name=job.event_name,
        issue_date=job.issue_date,
        issuer_name=job.issuer_name,
        certificate_title=job.certificate_title,
        description=job.description,
        status=job.status,
        total_recipients=job.total_recipients,
        processed_recipients=job.processed_recipients,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        progress_percentage=job.progress_percentage,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        status_url=_build_status_url(request, job.id),
        download_all_url=download_all_url,
        certificates=recipient_responses,
    )


@router.get(
    "/jobs",
    response_model=List[CertificateJobSummary],
    summary="List all certificate generation jobs",
)
def list_jobs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> List[CertificateJobSummary]:
    """Retrieve a paginated list of certificate jobs."""
    query = db.query(CertificateJob)
    if status_filter:
        query = query.filter(CertificateJob.status == status_filter)

    jobs = query.order_by(CertificateJob.created_at.desc()).offset(skip).limit(limit).all()

    return [
        CertificateJobSummary(
            id=job.id,
            event_name=job.event_name,
            issuer_name=job.issuer_name,
            certificate_title=job.certificate_title,
            issue_date=job.issue_date,
            status=job.status,
            total_recipients=job.total_recipients,
            processed_recipients=job.processed_recipients,
            successful_count=job.successful_count,
            failed_count=job.failed_count,
            progress_percentage=job.progress_percentage,
            created_at=job.created_at,
            completed_at=job.completed_at,
            status_url=_build_status_url(request, job.id),
        )
        for job in jobs
    ]


@router.get(
    "/certificates/{certificate_id}/download",
    summary="Download an individual generated certificate PDF",
    description="Stream or download a single recipient certificate PDF.",
)
def download_certificate(
    certificate_id: str,
    inline: bool = Query(False, description="View inline in browser if True, else download as attachment"),
    db: Session = Depends(get_db),
):
    """Retrieve and stream the generated PDF for an individual certificate."""
    cert = db.query(RecipientCertificate).filter(RecipientCertificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found.",
        )

    if cert.status in (CertificateStatus.PENDING, CertificateStatus.GENERATING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate is currently being generated. Please retry shortly.",
        )

    if cert.status == CertificateStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Certificate generation failed for this recipient: {cert.error_message}",
        )

    if not cert.file_path or not Path(cert.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated certificate file was not found on server storage.",
        )

    safe_name = StorageService.sanitize_filename(cert.recipient_name)
    download_filename = f"{safe_name}_{cert.certificate_number or 'certificate'}.pdf"
    disposition = "inline" if inline else f'attachment; filename="{download_filename}"'

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=download_filename,
        headers={"Content-Disposition": disposition},
    )


@router.get(
    "/jobs/{job_id}/download-all",
    summary="Download all generated certificates as a ZIP archive",
    description="Retrieve all successfully generated certificates in a bulk job packaged into a single ZIP file.",
)
def download_all_certificates(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Download a ZIP archive containing all completed certificates in the job."""
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    if job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is still in progress (Progress: {job.progress_percentage}%). Archive will be available once generation completes.",
        )

    if job.successful_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certificates were successfully generated for this job.",
        )

    if job.zip_file_path and Path(job.zip_file_path).exists():
        zip_path = Path(job.zip_file_path)
    else:
        valid_certs = [
            (c.recipient_name, c.certificate_number, Path(c.file_path))
            for c in job.certificates
            if c.status == CertificateStatus.COMPLETED and c.file_path
        ]
        created_zip = StorageService.create_job_zip(job.id, valid_certs)
        if not created_zip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unable to locate generated certificate files to package into ZIP archive.",
            )
        job.zip_file_path = str(created_zip)
        db.commit()
        zip_path = created_zip

    safe_event_name = StorageService.sanitize_filename(job.event_name)
    download_filename = f"certificates_{safe_event_name}_{job.id[:8]}.zip"

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=download_filename,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )
