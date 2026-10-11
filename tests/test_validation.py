"""Tests for input validation across job submissions."""
from fastapi.testclient import TestClient


def test_validation_empty_recipients_list(client: TestClient):
    """Submitting empty recipient list must return 422 Unprocessable Entity."""
    payload = {
        "event_name": "Web Dev Camp",
        "issuer_name": "Dev Org",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "details" in data
    assert any("recipients" in d["field"] for d in data["details"])


def test_validation_missing_required_fields(client: TestClient):
    """Missing event_name or issuer_name must fail validation."""
    response = client.post("/api/v1/jobs", json={"recipients": [{"name": "A", "email": "a@test.com"}]})
    assert response.status_code == 422
    data = response.json()
    fields = [d["field"] for d in data["details"]]
    assert any("event_name" in f for f in fields)
    assert any("issuer_name" in f for f in fields)


def test_validation_invalid_recipient_email(client: TestClient):
    """Recipient with invalid email format must be rejected."""
    payload = {
        "event_name": "Data Analytics",
        "issuer_name": "Data School",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "Invalid User", "email": "not-an-email-address"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("Invalid email address format" in d["message"] for d in data["details"])


def test_validation_empty_or_whitespace_name(client: TestClient):
    """Recipient with empty or whitespace-only name must be rejected."""
    payload = {
        "event_name": "Data Analytics",
        "issuer_name": "Data School",
        "recipients": [{"name": "   ", "email": "valid@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("cannot be empty" in d["message"] for d in data["details"])


def test_validation_whitespace_only_event_name(client: TestClient):
    """Whitespace-only event name must be rejected."""
    payload = {
        "event_name": "   ",
        "issuer_name": "Data School",
        "recipients": [{"name": "Valid User", "email": "valid@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
