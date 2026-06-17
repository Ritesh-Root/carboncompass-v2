"""
GET /api/health — Application health check endpoint.

Returns the availability status of all integrated Google Cloud services.
Designed for Cloud Run health checks and monitoring dashboards.
"""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    timestamp: datetime
    services: dict[str, bool]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    description="Returns service availability status. Used by Cloud Run readiness probes.",
)
async def health_check() -> HealthResponse:
    """
    Return health status of the application and all integrated Google Cloud services.

    The 'services' map reflects feature flag configuration — a service marked
    True indicates it is both enabled and expected to be available.
    """
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(tz=UTC),
        services={
            "gemini": settings.USE_GEMINI,
            "firestore": settings.USE_FIRESTORE,
            "bigquery": settings.USE_BIGQUERY,
            "pubsub": settings.USE_PUBSUB,
        },
    )
