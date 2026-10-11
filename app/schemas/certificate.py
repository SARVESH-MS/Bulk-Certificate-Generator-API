import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.models.enums import JobStatus, CertificateStatus

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class RecipientInput(BaseModel):
    """Input payload for a certificate recipient."""

    name: str = Field(..., min_length=1, max_length=150, description="Full name of recipient")
    email: str = Field(..., min_length=3, max_length=255, description="Recipient email address")
    identifier: Optional[str] = Field(None, max_length=100, description="Optional recipient ID or roll number")
    custom_attributes: Optional[Dict[str, Any]] = Field(
        None, description="Optional key-value metadata (e.g. grade, honors, hours)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Recipient name cannot be empty or whitespace only.")
        return trimmed

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not EMAIL_REGEX.match(trimmed):
            raise ValueError(f"Invalid email address format: '{v}'")
        return trimmed


class CertificateJobCreate(BaseModel):
    """Payload to request bulk certificate generation."""

    event_name: str = Field(..., min_length=2, max_length=255, description="Name of the event, course, or workshop")
    issue_date: Optional[str] = Field(
        default_factory=lambda: date.today().strftime("%B %d, %Y"),
        description="Issue date (YYYY-MM-DD or readable string). Defaults to current date if omitted.",
    )
    issuer_name: str = Field(..., min_length=2, max_length=255, description="Organization or authority issuing certificates")
    certificate_title: Optional[str] = Field(
        "Certificate of Completion",
        max_length=255,
        description="Headline certificate title",
    )
    description: Optional[str] = Field(
        "For successfully participating in and completing the program with distinction.",
        description="Body statement for the certificate",
    )
    recipients: List[RecipientInput] = Field(
        ...,
        min_length=1,
        description="List of recipients to generate certificates for",
    )

    @field_validator("event_name", "issuer_name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or whitespace only.")
        return trimmed

    @field_validator("issue_date")
    @classmethod
    def default_issue_date(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return date.today().strftime("%B %d, %Y")
        return v.strip()


class RecipientCertificateResponse(BaseModel):
    """Individual certificate status & download details."""

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    recipient_identifier: Optional[str] = None
    certificate_number: Optional[str] = None
    status: CertificateStatus
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime
    generated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CertificateJobResponse(BaseModel):
    """Detailed response for a bulk generation job, including progress and certificates."""

    id: str
    event_name: str
    issue_date: str
    issuer_name: str
    certificate_title: str
    description: Optional[str] = None
    status: JobStatus
    total_recipients: int
    processed_recipients: int
    successful_count: int
    failed_count: int
    progress_percentage: float
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    status_url: str
    download_all_url: Optional[str] = None
    certificates: List[RecipientCertificateResponse] = []

    model_config = ConfigDict(from_attributes=True)


class JobCreateAcceptedResponse(BaseModel):
    """Response returned upon accepting a bulk job (HTTP 202)."""

    job_id: str
    status: JobStatus
    message: str
    total_recipients: int
    status_url: str
    created_at: datetime


class CertificateJobSummary(BaseModel):
    """Lightweight summary of a job for list endpoints."""

    id: str
    event_name: str
    issuer_name: str
    certificate_title: str
    issue_date: str
    status: JobStatus
    total_recipients: int
    processed_recipients: int
    successful_count: int
    failed_count: int
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    status_url: str

    model_config = ConfigDict(from_attributes=True)
