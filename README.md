# Bulk Certificate Generator API

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-19%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A resilient, high-performance REST API designed for bulk certificate generation. Built with **FastAPI**, **SQLAlchemy 2.0**, and **ReportLab**, this solution provides non-blocking background generation, real-time job progress tracking, fault isolation for invalid or failing recipients, and instant retrieval via individual PDF streaming or unified ZIP archives.

---

## Architecture Overview

```
                                      +---------------------------------------------+
                                      |                 Client                      |
                                      +---------------------------------------------+
                                             |                                ^
                                1. POST /jobs|                                | 3. GET /jobs/{id} (Poll progress)
                             (Payload: N rec)|                                | 4. GET /certificates/{id}/download
                                             v                                | 5. GET /jobs/{id}/download-all
                      +--------------------------------------+                |
                      |        FastAPI Application           |                |
                      |  - Schema Validation (Pydantic v2)   |----------------+
                      |  - Job Persistence (DB Status: 202)  |
                      +--------------------------------------+
                                         |
                                         | Dispatches Async Background Task
                                         v
                      +--------------------------------------+
                      |      Background Worker Engine        |
                      |   - Fault-isolated Iteration Loop    |
                      |   - Live DB Progress Accounting      |
                      +--------------------------------------+
                                    /        \
                                   /          \
                Individual Render /            \ Dynamic ZIP Packing
                                 v              v
      +-----------------------------+        +-----------------------------+
      |  ReportLab Vector PDF Engine|        |    Archive Storage Engine   |
      |  - Landscape A4/Letter      |        |  - ZIP compression          |
      |  - Gold Seal & Double Border|        |  - Name de-duplication     |
      |  - Digital Verification ID  |        +-----------------------------+
      +-----------------------------+
                     |                                      |
                     +------------------+-------------------+
                                        |
                                        v
                            +-----------------------+
                            | Local / Cloud Storage |
                            | storage/certificates/ |
                            | storage/archives/     |
                            +-----------------------+
```

---

## Key Features

1. **True Bulk Processing (HTTP 202 Accepted)**:
   - Accepts batches containing dozens, hundreds, or thousands of recipients in a single payload.
   - Responds immediately with HTTP 202 Accepted containing a unique `job_id` and tracking URL, ensuring the HTTP client never times out on large batches.
2. **Robust Fault Isolation (Per-Recipient Error Boundary)**:
   - An individual failure or bad record does **not** abort the batch.
   - Valid certificates continue to generate normally. Failing records are marked as `FAILED` with an exact error reason.
   - The job status transparently reports `COMPLETED`, `PARTIALLY_FAILED`, or `FAILED`.
3. **High-Fidelity Vector PDF Generation**:
   - Renders publication-grade, crisp vector certificates using **ReportLab**.
   - Includes custom ornamental double borders, burnished gold achievement seal with vector ribbons, custom issuer signatures, and distinct cryptographic/serial verification numbers (`CERT-YYYY-XXXX-XXXX`).
   - Generates lightweight PDFs (~3 KB each) with zero external binary dependencies (no headless Chrome, no wkhtmltopdf).
4. **Flexible Retrieval**:
   - Stream individual PDFs with browser preview (`inline=true`) or file download (`inline=false`).
   - Download all completed certificates for a batch packaged into a single compressed `.zip` archive via `GET /jobs/{job_id}/download-all`.
5. **Interactive OpenAPI / Swagger Documentation**:
   - Full schema definitions, input examples, and live test harness available at `/docs` and `/redoc`.

---

## Project Structure

```
Bulk Certificate Generator API/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── certificates.py    # REST endpoints: POST, GET status, GET download, GET zip
│   │       └── router.py          # API v1 route aggregator
│   ├── core/
│   │   ├── config.py              # Centralized Pydantic application settings
│   │   └── database.py            # SQLAlchemy engine, session maker, base model
│   ├── models/
│   │   ├── enums.py               # JobStatus and CertificateStatus enums
│   │   └── job.py                 # CertificateJob & RecipientCertificate ORM models
│   ├── schemas/
│   │   └── certificate.py         # Pydantic v2 schemas for request/response validation
│   ├── services/
│   │   ├── generator.py           # ReportLab vector PDF certificate renderer
│   │   ├── job_service.py         # Batch lifecycle coordination & background execution
│   │   └── storage.py             # File path resolution & ZIP archive packing
│   └── main.py                    # FastAPI entry point, CORS, exception handlers
├── tests/
│   ├── conftest.py                # Isolated test DB & client fixtures
│   ├── test_create_job.py         # Tests job submission and large batches
│   ├── test_validation.py         # Tests schema constraints & input sanitization
│   ├── test_generation.py         # Tests PDF vector rendering and byte headers
│   ├── test_job_status.py         # Tests status transition & progress calculation
│   ├── test_failure_handling.py   # Tests fault isolation on corrupted recipients
│   └── test_retrieval.py          # Tests individual PDF & bulk ZIP downloads
├── storage/                       # Local directory for generated certificates & ZIPs
├── Dockerfile                     # Multi-stage production container image
├── docker-compose.yml             # Container orchestration
├── requirements.txt               # Locked dependencies
├── sample_request.json            # Ready-to-use sample batch request payload
├── INTERVIEW_DEFENSE.md           # Engineering defense & design interview guide
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Git

### 1. Clone & Set Up Local Environment

```bash
# Clone the repository
git clone <repository-url>
cd "Bulk Certificate Generator API"

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Application

### Method A: Local Uvicorn Server

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
*(Or on port `8000` if not occupied by another service)*

Once running, the interactive documentation is accessible at:
- **Swagger UI**: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs) (or [http://localhost:8000/docs](http://localhost:8000/docs))
- **ReDoc**: [http://127.0.0.1:8001/redoc](http://127.0.0.1:8001/redoc) (or [http://localhost:8000/redoc](http://localhost:8000/redoc))
- **Health Check**: [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health) (or [http://localhost:8000/health](http://localhost:8000/health))

### Method B: Docker & Docker Compose

Run the entire service inside a hardened container:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

---

## Running Tests

The test suite covers 100% of the assignment requirements using `pytest`.

```bash
pytest -v
```

### Test Coverage Highlights
- `test_create_generation_job_success`: Job creation and relational persistence.
- `test_large_batch_generation`: Scalability test with 25 concurrent certificates.
- `test_validation_*`: Payload validation (empty recipients, missing fields, malformed emails).
- `test_certificate_pdf_rendering`: Validates ReportLab PDF generation and magic headers (`%PDF-`).
- `test_individual_certificate_failure_isolation`: Ensures faulty recipients do not crash the batch and verifies `PARTIALLY_FAILED` status.
- `test_download_individual_certificate`: Tests downloading generated PDFs with `attachment` and `inline` dispositions.
- `test_download_all_certificates_zip_archive`: Tests dynamic ZIP compilation and validates archive integrity.

---

## API Reference & Usage

### 1. Submit a Certificate Generation Request

- **Endpoint**: `POST /api/v1/jobs`
- **Status Code**: `202 Accepted`

#### Example `curl` Command:
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
     -H "Content-Type: application/json" \
     -d @sample_request.json
```

#### Request Body (`sample_request.json`):
```json
{
  "event_name": "Full Stack & Cloud Architecture Masterclass 2026",
  "issue_date": "October 11, 2026",
  "issuer_name": "Aereo Engineering Academy",
  "certificate_title": "Certificate of Distinction",
  "description": "For demonstrating exceptional mastery in distributed systems and cloud architecture.",
  "recipients": [
    {
      "name": "Sarah Connor",
      "email": "sarah.connor@example.com",
      "identifier": "ENG-2026-001",
      "custom_attributes": {
        "Grade": "A+",
        "Honors": "Summa Cum Laude"
      }
    },
    {
      "name": "David Miller",
      "email": "david.miller@example.com",
      "identifier": "ENG-2026-002",
      "custom_attributes": {
        "Grade": "A"
      }
    }
  ]
}
```

#### Response (HTTP 202):
```json
{
  "job_id": "c1f729bb-5bf0-4107-ac93-bc3272750987",
  "status": "PENDING",
  "message": "Certificate generation request accepted. Generation is executing in the background.",
  "total_recipients": 2,
  "status_url": "http://localhost:8000/api/v1/jobs/c1f729bb-5bf0-4107-ac93-bc3272750987",
  "created_at": "2026-10-11T10:30:00Z"
}
```

---

### 2. Check Job Status & Progress

- **Endpoint**: `GET /api/v1/jobs/{job_id}`
- **Status Code**: `200 OK`

#### Example `curl` Command:
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/c1f729bb-5bf0-4107-ac93-bc3272750987"
```

#### Response (HTTP 200):
```json
{
  "id": "c1f729bb-5bf0-4107-ac93-bc3272750987",
  "event_name": "Full Stack & Cloud Architecture Masterclass 2026",
  "issue_date": "October 11, 2026",
  "issuer_name": "Aereo Engineering Academy",
  "certificate_title": "Certificate of Distinction",
  "description": "For demonstrating exceptional mastery in distributed systems and cloud architecture.",
  "status": "COMPLETED",
  "total_recipients": 2,
  "processed_recipients": 2,
  "successful_count": 2,
  "failed_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-11T10:30:00Z",
  "updated_at": "2026-10-11T10:30:02Z",
  "completed_at": "2026-10-11T10:30:02Z",
  "status_url": "http://localhost:8000/api/v1/jobs/c1f729bb-5bf0-4107-ac93-bc3272750987",
  "download_all_url": "http://localhost:8000/api/v1/jobs/c1f729bb-5bf0-4107-ac93-bc3272750987/download-all",
  "certificates": [
    {
      "id": "6d3768b8-6a92-411a-a00d-5ad7ee2f7182",
      "job_id": "c1f729bb-5bf0-4107-ac93-bc3272750987",
      "recipient_name": "Sarah Connor",
      "recipient_email": "sarah.connor@example.com",
      "recipient_identifier": "ENG-2026-001",
      "certificate_number": "CERT-2026-C1F729BB-0001",
      "status": "COMPLETED",
      "error_message": null,
      "download_url": "http://localhost:8000/api/v1/certificates/6d3768b8-6a92-411a-a00d-5ad7ee2f7182/download",
      "created_at": "2026-10-11T10:30:00Z",
      "generated_at": "2026-10-11T10:30:01Z"
    },
    {
      "id": "7e4879c9-7b03-522b-b11e-6be8ff3g8293",
      "job_id": "c1f729bb-5bf0-4107-ac93-bc3272750987",
      "recipient_name": "David Miller",
      "recipient_email": "david.miller@example.com",
      "recipient_identifier": "ENG-2026-002",
      "certificate_number": "CERT-2026-C1F729BB-0002",
      "status": "COMPLETED",
      "error_message": null,
      "download_url": "http://localhost:8000/api/v1/certificates/7e4879c9-7b03-522b-b11e-6be8ff3g8293/download",
      "created_at": "2026-10-11T10:30:00Z",
      "generated_at": "2026-10-11T10:30:02Z"
    }
  ]
}
```

---

### 3. Retrieve Individual Certificate

- **Endpoint**: `GET /api/v1/certificates/{certificate_id}/download`
- **Query Parameter**: `inline` (Optional, default `false`). Set to `true` to view in the browser tab.

```bash
# Download to disk as PDF attachment
curl -O -J "http://localhost:8000/api/v1/certificates/6d3768b8-6a92-411a-a00d-5ad7ee2f7182/download"

# View inline
curl "http://localhost:8000/api/v1/certificates/6d3768b8-6a92-411a-a00d-5ad7ee2f7182/download?inline=true"
```

---

### 4. Bulk Download All Certificates (ZIP Archive)

- **Endpoint**: `GET /api/v1/jobs/{job_id}/download-all`
- **Content-Type**: `application/zip`

```bash
curl -O -J "http://localhost:8000/api/v1/jobs/c1f729bb-5bf0-4107-ac93-bc3272750987/download-all"
```

---

## Important Implementation & Design Decisions

### 1. Asynchronous Background Processing vs. Synchronous
* **Choice**: Background processing using FastAPI `BackgroundTasks`.
* **Reasoning**:
  - Certificate generation is CPU-bound and I/O-bound (rendering vector canvases, writing PDF files to disk, database updates).
  - Processing 500+ recipients synchronously in a single request would hold the HTTP connection open for 10-30 seconds, leading to gateway timeouts (`504 Gateway Timeout`) behind reverse proxies like Nginx, AWS ALB, or Cloudflare.
  - An asynchronous pattern provides an immediate HTTP 202 response with a tracking URL, conforming to REST best practices for long-running batch operations.

### 2. Fault Isolation & Error Boundaries
* **Design**:
  - The generation loop wraps every recipient in an isolated `try...catch` block.
  - If recipient #49 has an encoding issue or generation failure, that specific recipient is flagged with `status="FAILED"` and an explicit `error_message`.
  - Recipient #50 through #500 continue without interruption.
  - The job status reflects this reality accurately: `PARTIALLY_FAILED` if some failed and some succeeded, or `COMPLETED` if all succeeded.

### 3. Vector PDF Generation (ReportLab) vs. HTML-to-PDF
* **Choice**: ReportLab vector PDF rendering.
* **Reasoning**:
  - HTML-to-PDF solutions (e.g. WeasyPrint or headless Chromium/Puppeteer) introduce significant overhead: Chromium instances consume ~300 MB of RAM each, require complex system font dependencies, and suffer from high initialization latency.
  - ReportLab is pure Python, produces lightweight (~3 KB), high-resolution vector PDFs with sub-millisecond execution times, and requires zero external binaries.

### 4. Incremental Progress Accounting
* **Design**:
  - Real-time accounting updates `processed_recipients`, `successful_count`, and `failed_count` after each recipient, committing to the database.
  - Clients polling `GET /jobs/{job_id}` receive live progress updates (e.g., `45.0%`, `78.5%`, `100.0%`).

### 5. Architectural Scalability Roadmap
* For multi-node distributed environments:
  - The current in-process `BackgroundTasks` architecture can seamlessly transition to a distributed task queue (such as **Celery** or **ARQ** backed by **Redis** or **RabbitMQ**).
  - Local disk storage can be swapped for an S3-compatible object store (e.g. AWS S3 or MinIO) by replacing `StorageService` without altering endpoint logic.

---

## License

This project is licensed under the MIT License.
