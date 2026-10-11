from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core import database
from app.api.v1.router import api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("bulk_certificate_generator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Bulk Certificate Generator API...")
    database.init_db()
    settings.init_storage()
    logger.info("Database and storage directories successfully initialized.")
    yield
    logger.info("Shutting down Bulk Certificate Generator API.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = []
    for error in exc.errors():
        loc = " -> ".join(str(item) for item in error.get("loc", []))
        formatted_errors.append(
            {
                "field": loc,
                "message": error.get("msg", "Validation failed"),
                "type": error.get("type", "value_error"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "Validation Error",
            "message": "The submitted certificate request payload contains invalid fields.",
            "details": formatted_errors,
        },
    )


@app.get("/", tags=["General"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "documentation": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "create_job": f"POST {settings.API_V1_STR}/jobs",
            "get_job_status": f"GET {settings.API_V1_STR}/jobs/{{job_id}}",
            "list_jobs": f"GET {settings.API_V1_STR}/jobs",
            "download_certificate": f"GET {settings.API_V1_STR}/certificates/{{certificate_id}}/download",
            "download_all_zip": f"GET {settings.API_V1_STR}/jobs/{{job_id}}/download-all",
        },
    }


@app.get("/health", tags=["General"])
def health_check():
    db_status = "healthy"
    try:
        db = database.SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    storage_status = "accessible" if settings.STORAGE_DIR.exists() else "inaccessible"

    return {
        "status": "healthy" if db_status == "healthy" and storage_status == "accessible" else "degraded",
        "database": db_status,
        "storage": storage_status,
        "version": settings.VERSION,
    }


app.include_router(api_v1_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
