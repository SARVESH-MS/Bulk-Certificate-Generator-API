from fastapi.testclient import TestClient
from app.core.config import settings
from app.models.enums import JobStatus, CertificateStatus
from app.models.job import CertificateJob, RecipientCertificate


def test_root_discovery_endpoint(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "documentation" in data
    assert "endpoints" in data
    assert "create_job" in data["endpoints"]


def test_health_check_endpoint(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert data["storage"] == "accessible"


def test_job_status_filter_and_omitting_recipients(client: TestClient, sample_payload: dict):
    post_res = client.post("/api/v1/jobs", json=sample_payload)
    job_id = post_res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}?include_recipients=false")
    assert status_res.status_code == 200
    assert len(status_res.json()["certificates"]) == 0

    filter_res = client.get("/api/v1/jobs?status=COMPLETED")
    assert filter_res.status_code == 200
    assert len(filter_res.json()) >= 1


def test_download_all_in_progress_conflict(client: TestClient, db_session):
    job = CertificateJob(
        event_name="Processing Job",
        issue_date="October 11, 2026",
        issuer_name="Org",
        status=JobStatus.PROCESSING,
        total_recipients=10,
        processed_recipients=2,
    )
    db_session.add(job)
    db_session.commit()

    res = client.get(f"/api/v1/jobs/{job.id}/download-all")
    assert res.status_code == 409
    assert "in progress" in res.json()["detail"].lower()


def test_download_all_zero_successes(client: TestClient, db_session):
    job = CertificateJob(
        event_name="Failed Job",
        issue_date="October 11, 2026",
        issuer_name="Org",
        status=JobStatus.FAILED,
        total_recipients=5,
        processed_recipients=5,
        successful_count=0,
        failed_count=5,
    )
    db_session.add(job)
    db_session.commit()

    res = client.get(f"/api/v1/jobs/{job.id}/download-all")
    assert res.status_code == 404
    assert "no certificates were successfully generated" in res.json()["detail"].lower()


def test_download_pending_certificate_conflict(client: TestClient, db_session):
    job = CertificateJob(
        event_name="Queued Job",
        issue_date="October 11, 2026",
        issuer_name="Org",
        status=JobStatus.PENDING,
        total_recipients=1,
    )
    db_session.add(job)
    db_session.flush()

    cert = RecipientCertificate(
        job_id=job.id,
        recipient_name="Pending Recipient",
        recipient_email="pending@test.com",
        status=CertificateStatus.PENDING,
    )
    db_session.add(cert)
    db_session.commit()

    res = client.get(f"/api/v1/certificates/{cert.id}/download")
    assert res.status_code == 409
    assert "currently being generated" in res.json()["detail"].lower()


def test_batch_size_exceeding_limit(client: TestClient):
    original_limit = settings.MAX_RECIPIENTS_PER_BATCH
    try:
        settings.MAX_RECIPIENTS_PER_BATCH = 2
        payload = {
            "event_name": "Overloaded Job",
            "issuer_name": "Test Org",
            "recipients": [
                {"name": "User 1", "email": "u1@test.com"},
                {"name": "User 2", "email": "u2@test.com"},
                {"name": "User 3", "email": "u3@test.com"},
            ],
        }
        res = client.post("/api/v1/jobs", json=payload)
        assert res.status_code == 400
        assert "exceeds maximum allowed limit" in res.json()["detail"]
    finally:
        settings.MAX_RECIPIENTS_PER_BATCH = original_limit
