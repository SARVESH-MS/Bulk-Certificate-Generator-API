from fastapi.testclient import TestClient
from app.services.job_service import JobService


def test_job_not_found(client: TestClient):
    response = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_job_status_and_progress_tracking(client: TestClient, sample_payload: dict):
    post_res = client.post("/api/v1/jobs", json=sample_payload)
    assert post_res.status_code == 202
    job_id = post_res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    assert job_data["id"] == job_id
    assert job_data["total_recipients"] == 2
    assert job_data["status"] == "COMPLETED"
    assert job_data["successful_count"] == 2
    assert job_data["failed_count"] == 0
    assert job_data["processed_recipients"] == 2
    assert job_data["progress_percentage"] == 100.0
    assert job_data["completed_at"] is not None
    assert job_data["download_all_url"] is not None

    recipients = job_data["certificates"]
    assert len(recipients) == 2
    for r in recipients:
        assert r["status"] == "COMPLETED"
        assert r["download_url"] is not None
        assert r["certificate_number"].startswith("CERT-")


def test_list_jobs(client: TestClient, sample_payload: dict):
    client.post("/api/v1/jobs", json=sample_payload)
    list_res = client.get("/api/v1/jobs?skip=0&limit=10")
    assert list_res.status_code == 200
    jobs = list_res.json()
    assert len(jobs) >= 1
    assert "status_url" in jobs[0]
