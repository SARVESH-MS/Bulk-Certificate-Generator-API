import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import JobStatus, CertificateStatus


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CertificateJob(Base):
    __tablename__ = "certificate_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_name = Column(String(255), nullable=False)
    issue_date = Column(String(50), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    certificate_title = Column(String(255), nullable=False, default="Certificate of Completion")
    description = Column(Text, nullable=True)

    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    total_recipients = Column(Integer, default=0, nullable=False)
    processed_recipients = Column(Integer, default=0, nullable=False)
    successful_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at = Column(DateTime, nullable=True)
    zip_file_path = Column(String(500), nullable=True)

    certificates = relationship(
        "RecipientCertificate",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def progress_percentage(self) -> float:
        if self.total_recipients == 0:
            return 100.0
        return round((self.processed_recipients / self.total_recipients) * 100, 2)


class RecipientCertificate(Base):
    __tablename__ = "recipient_certificates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("certificate_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_identifier = Column(String(100), nullable=True)
    custom_attributes = Column(Text, nullable=True)

    certificate_number = Column(String(100), unique=True, nullable=True, index=True)
    status = Column(SQLEnum(CertificateStatus), default=CertificateStatus.PENDING, nullable=False, index=True)
    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    generated_at = Column(DateTime, nullable=True)

    job = relationship("CertificateJob", back_populates="certificates")
