"""V1 API Router aggregation."""
from fastapi import APIRouter
from app.api.v1.certificates import router as certificates_router

api_v1_router = APIRouter()
api_v1_router.include_router(certificates_router)
