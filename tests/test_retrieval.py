import io
import zipfile
from fastapi.testclient import TestClient


def test_download_individual_certificate(client: TestClient, sample_payload: dict):
    post_res = client.post("/api/v1/jobs", json=sample_payload)
    job_id = post_res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    cert_id = status_res.json()["certificates"][0]["id"]

    dl_res = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert "attachment" in dl_res.headers["content-disposition"]
    assert dl_res.content.startswith(b"%PDF-")

    inline_res = client.get(f"/api/v1/certificates/{cert_id}/download?inline=true")
    assert inline_res.status_code == 200
    assert "inline" in inline_res.headers["content-disposition"]


def test_download_certificate_not_found(client: TestClient):
    res = client.get("/api/v1/certificates/00000000-0000-0000-0000-000000000000/download")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_download_failed_certificate_error_response(client: TestClient):
    payload = {
        "event_name": "Failure Test",
        "issuer_name": "Test Org",
        "recipients": [{"name": "__FORCE_FAIL__", "email": "fail@test.com"}],
    }
    post_res = client.post("/api/v1/jobs", json=payload)
    job_id = post_res.json()["job_id"]

    status_res = client.get(f"/api/v1/jobs/{job_id}")
    failed_cert_id = status_res.json()["certificates"][0]["id"]

    dl_res = client.get(f"/api/v1/certificates/{failed_cert_id}/download")
    assert dl_res.status_code == 422
    assert "generation failed" in dl_res.json()["detail"].lower()


def test_download_all_certificates_zip_archive(client: TestClient, sample_payload: dict):
    post_res = client.post("/api/v1/jobs", json=sample_payload)
    job_id = post_res.json()["job_id"]

    zip_res = client.get(f"/api/v1/jobs/{job_id}/download-all")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert "attachment" in zip_res.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(zip_res.content), "r") as z:
        file_list = z.namelist()
        assert len(file_list) == 2
        for filename in file_list:
            assert filename.endswith(".pdf")
            file_bytes = z.read(filename)
            assert file_bytes.startswith(b"%PDF-")


def test_download_all_non_existent_job(client: TestClient):
    res = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000/download-all")
    assert res.status_code == 404
