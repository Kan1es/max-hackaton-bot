import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.health import build_health
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine, get_db
from app.db.seed import seed_support_programs
from app.models.base import Base
from app.schemas.health import HealthResponse

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks.

    The schema itself comes from Alembic (`alembic upgrade head` runs before
    uvicorn in docker-compose). create_all is only a convenience for someone
    poking at the app locally with DEBUG=True and no migration run.
    """
    if settings.DEBUG:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception:
            logger.warning("Failed to auto-create tables on startup", exc_info=True)
    try:
        async with AsyncSessionLocal() as session:
            await seed_support_programs(session)
    except Exception:
        logger.warning("Failed to seed support programs", exc_info=True)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# The mini-app authenticates with an `Authorization: tma <initData>` header,
# not cookies, so credentials stay off — which also keeps the wildcard origin
# a legal CORS configuration. Set CORS_ORIGINS to the real mini-app origin in
# production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Service-Token", "X-Max-User-Id"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def root_health_check(db: AsyncSession = Depends(get_db)):
    """Root health check, for container probes that can't be told a prefix."""
    return await build_health(db)


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }
