"""Tests for creating certificate generation jobs."""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.job import CertificateJob, RecipientCertificate


def test_create_generation_job_success(client: TestClient, db_session: Session, sample_payload: dict):
    """Test successful submission of a bulk certificate generation job."""
    response = client.post("/api/v1/jobs", json=sample_payload)

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["total_recipients"] == 2
    assert "status_url" in data
    assert data["message"] == "Certificate generation request accepted. Generation is executing in the background."

    job_id = data["job_id"]
    job = db_session.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    assert job is not None
    assert job.event_name == sample_payload["event_name"]
    assert job.total_recipients == 2

    recipients = db_session.query(RecipientCertificate).filter(RecipientCertificate.job_id == job_id).all()
    assert len(recipients) == 2
    names = {r.recipient_name for r in recipients}
    assert "Jane Doe" in names
    assert "John Smith" in names


def test_create_job_default_date_and_title(client: TestClient, sample_payload: dict):
    """Test that issue_date and certificate_title fall back to defaults when omitted."""
    payload = {
        "event_name": "Python FastTrack",
        "issuer_name": "Code Academy",
        "recipients": [{"name": "Alice Wonderland", "email": "alice@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = client.get(f"/api/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    job_data = status_response.json()
    assert job_data["certificate_title"] == "Certificate of Completion"
    assert job_data["issue_date"] is not None


def test_large_batch_generation(client: TestClient):
    """Test generating a batch of 25 recipients with custom attributes."""
    recipients = [
        {
            "name": f"Recipient #{i:02d}",
            "email": f"recipient_{i:02d}@example.com",
            "identifier": f"ID-{1000 + i}",
            "custom_attributes": {"Score": f"{80 + (i % 20)}%", "Tier": "Gold" if i % 2 == 0 else "Silver"},
        }
        for i in range(1, 26)
    ]
    payload = {
        "event_name": "Cloud Native Architecture Masterclass",
        "issuer_name": "Aereo Cloud Institute",
        "certificate_title": "Certificate of Specialization",
        "recipients": recipients,
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = client.get(f"/api/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    job_data = status_response.json()
    assert job_data["status"] == "COMPLETED"
    assert job_data["total_recipients"] == 25
    assert job_data["successful_count"] == 25
    assert job_data["failed_count"] == 0
    assert len(job_data["certificates"]) == 25

