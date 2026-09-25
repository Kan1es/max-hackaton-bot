from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.application import Application
from app.models.profile import Profile
from app.models.support_program import SupportProgram
from app.schemas.application import ApplicationCreate, ApplicationRead

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("/", response_model=ApplicationRead)
async def create_application(payload: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    """Save a program into "Мои заявки" (idempotent per profile+program)."""
    if await db.get(Profile, payload.profile_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if await db.get(SupportProgram, payload.program_id) is None:
        raise HTTPException(status_code=404, detail="Program not found")

    result = await db.execute(
        select(Application).where(
            Application.profile_id == payload.profile_id,
            Application.program_id == payload.program_id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        application = Application(
            profile_id=payload.profile_id,
            program_id=payload.program_id,
            status=payload.status,
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.program))
        .where(Application.id == application.id)
    )
    return result.scalar_one()


@router.get("/{profile_id}", response_model=list[ApplicationRead])
async def list_applications(profile_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.program))
        .where(Application.profile_id == profile_id)
    )
    return result.scalars().all()
