from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.services.crawl.scheduler import start_local_scheduler, stop_local_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} in {settings.ENV} mode")
    scheduler = start_local_scheduler()
    yield
    if scheduler is not None:
        stop_local_scheduler(scheduler)
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Automated Syllabus-to-Industry Gap Analyzer API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/healthz", tags=["Health"])
async def healthcheck() -> dict[str, str]:
    """Liveness check endpoint."""
    return {
        "status": "ok",
        "environment": settings.ENV,
        "version": settings.VERSION,
    }
