from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.syllabi import router as syllabi_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(syllabi_router)
api_router.include_router(jobs_router)

__all__ = ["api_router"]
