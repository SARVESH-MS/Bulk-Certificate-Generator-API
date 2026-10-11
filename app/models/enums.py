from enum import Enum


class JobStatus(str, Enum):
    """Lifecycle status for a bulk certificate generation job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIALLY_FAILED = "PARTIALLY_FAILED"
    FAILED = "FAILED"


class CertificateStatus(str, Enum):
    """Generation status for an individual recipient's certificate."""

    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
