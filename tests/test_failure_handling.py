from fastapi.testclient import TestClient


def test_individual_certificate_failure_isolation(client: TestClient):
    payload = {
        "event_name": "Resilient Systems Workshop",
        "issuer_name": "Fault Tolerance Institute",
        "recipients": [
            {
                "name": "First Valid Recipient",
                "email": "first@example.com",
            },
            {
                "name": "__FORCE_FAIL__",
                "email": "fail@example.com",
            },
            {
                "name": "Second Valid Recipient",
                "email": "second@example.com",
            },
        ],
    }

    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    assert job_data["status"] == "PARTIALLY_FAILED"
    assert job_data["total_recipients"] == 3
    assert job_data["successful_count"] == 2
    assert job_data["failed_count"] == 1
    assert job_data["processed_recipients"] == 3
    assert job_data["progress_percentage"] == 100.0

    recipients = job_data["certificates"]
    assert len(recipients) == 3

    successes = [r for r in recipients if r["status"] == "COMPLETED"]
    failures = [r for r in recipients if r["status"] == "FAILED"]

    assert len(successes) == 2
    assert len(failures) == 1

    for s in successes:
        assert s["download_url"] is not None
        assert s["error_message"] is None

    failed_item = failures[0]
    assert failed_item["recipient_name"] == "__FORCE_FAIL__"
    assert failed_item["download_url"] is None
    assert "Simulated recipient-level processing failure" in failed_item["error_message"]


def test_all_recipients_failed_job_status(client: TestClient):
    payload = {
        "event_name": "Simulated Failure Workshop",
        "issuer_name": "Test Org",
        "recipients": [
            {"name": "__FORCE_FAIL__", "email": "f1@example.com"},
            {"name": "__FORCE_FAIL__", "email": "f2@example.com"},
        ],
    }
    res = client.post("/api/v1/jobs", json=payload)
    job_id = res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    job_data = status_res.json()

    assert job_data["status"] == "FAILED"
    assert job_data["successful_count"] == 0
    assert job_data["failed_count"] == 2
    assert job_data["download_all_url"] is None
