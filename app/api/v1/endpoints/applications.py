from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.profiles import get_or_create_profile
from app.core.database import get_db
from app.core.security import Caller, get_caller
from app.models.application import Application
from app.models.support_program import SupportProgram
from app.schemas.application import ApplicationCreate, ApplicationRead, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["Applications"])


async def _owned_application(db: AsyncSession, application_id: int, profile_id: int) -> Application:
    application = await db.get(Application, application_id)
    # A 404 rather than a 403 for someone else's row: the caller has no
    # business learning whether that id exists.
    if application is None or application.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("/", response_model=ApplicationRead)
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    caller: Caller = Depends(get_caller),
):
    """Save a program into "Мои заявки" for the caller (idempotent)."""
    profile = await get_or_create_profile(db, caller.max_user_id)
    if await db.get(SupportProgram, payload.program_id) is None:
        raise HTTPException(status_code=404, detail="Program not found")

    result = await db.execute(
        select(Application).where(
            Application.profile_id == profile.id,
            Application.program_id == payload.program_id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        application = Application(
            profile_id=profile.id,
            program_id=payload.program_id,
            status=payload.status,
        )
        db.add(application)
    await db.commit()

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.program))
        .where(Application.id == application.id)
    )
    return result.scalar_one()


@router.get("/", response_model=list[ApplicationRead])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    caller: Caller = Depends(get_caller),
):
    """The caller's saved programs, newest first."""
    profile = await get_or_create_profile(db, caller.max_user_id)
    await db.commit()
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.program))
        .where(Application.profile_id == profile.id)
        .order_by(Application.created_at.desc(), Application.id.desc())
    )
    return result.scalars().all()


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    caller: Caller = Depends(get_caller),
):
    """Move a saved program along the saved → in_progress → submitted track,
    and/or record which checklist documents are ready."""
    profile = await get_or_create_profile(db, caller.max_user_id)
    application = await _owned_application(db, application_id, profile.id)
    if payload.status is not None:
        application.status = payload.status
    if payload.checked_docs is not None:
        application.checked_docs = payload.checked_docs
    await db.commit()

    result = await db.execute(
        select(Application)
        .options(selectinload(Application.program))
        .where(Application.id == application.id)
    )
    return result.scalar_one()


@router.delete("/by-program/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application_by_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    caller: Caller = Depends(get_caller),
):
    """Un-save a program. Keyed by program id because that is what the
    mini-app's bookmark toggle knows about."""
    profile = await get_or_create_profile(db, caller.max_user_id)
    result = await db.execute(
        select(Application).where(
            Application.profile_id == profile.id,
            Application.program_id == program_id,
        )
    )
    application = result.scalar_one_or_none()
    if application is not None:
        await db.delete(application)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
