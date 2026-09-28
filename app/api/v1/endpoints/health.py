from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


async def build_health(db: AsyncSession) -> HealthResponse:
    """Shared by GET /health and GET /api/v1/health."""
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — health must report, not raise
        db_status = f"unhealthy: {exc}"

    return HealthResponse(status="ok", database=db_status, version=settings.VERSION)


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint verifying application and database status."""
    return await build_health(db)
