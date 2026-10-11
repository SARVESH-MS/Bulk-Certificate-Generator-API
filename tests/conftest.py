import shutil
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core import database
from app.main import app

temp_dir = tempfile.mkdtemp(prefix="cert_test_")
temp_path = Path(temp_dir)
test_db_path = temp_path / "test_certificates.db"

settings.DATABASE_URL = f"sqlite:///{test_db_path.as_posix()}"
settings.STORAGE_DIR = temp_path / "certificates"
settings.ZIP_STORAGE_DIR = temp_path / "archives"
settings.init_storage()

database.reconfigure_engine(settings.DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_environment():
    yield
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()
        with database.engine.begin() as conn:
            conn.execute(text("DELETE FROM recipient_certificates"))
            conn.execute(text("DELETE FROM certificate_jobs"))


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_payload() -> dict:
    return {
        "event_name": "Full Stack & Cloud Architecture Bootcamp",
        "issue_date": "October 11, 2026",
        "issuer_name": "Tech Academy Global",
        "certificate_title": "Certificate of Excellence",
        "description": "For outstanding capstone achievement and technical excellence.",
        "recipients": [
            {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "identifier": "STUDENT-101",
                "custom_attributes": {"Score": "98%", "Honors": "Gold Medal"},
            },
            {
                "name": "John Smith",
                "email": "john.smith@example.com",
                "identifier": "STUDENT-102",
                "custom_attributes": {"Score": "92%"},
            },
        ],
    }
