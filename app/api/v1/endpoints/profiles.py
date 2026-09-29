from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Caller, get_caller
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileRead, ProfileUpsert
from app.schemas.error import AUTH_ERRORS

router = APIRouter(prefix="/profile", tags=["Profile"])


async def get_or_create_profile(db: AsyncSession, max_user_id: int) -> Profile:
    """Resolve the profile of a MAX user, creating an empty one on first contact.

    Shared by every profile-scoped endpoint so that the profile is always
    derived from the authenticated caller instead of a client-supplied id.
    """
    result = await db.execute(select(User).where(User.max_user_id == max_user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(max_user_id=max_user_id)
        db.add(user)
        await db.flush()

    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.flush()
    return profile


@router.post("/", response_model=ProfileRead, responses=AUTH_ERRORS)
async def upsert_profile(
    payload: ProfileUpsert,
    db: AsyncSession = Depends(get_db),
    caller: Caller = Depends(get_caller),
):
    """Create or partially update the caller's profile.

    Called by the bot after every answered dialog step and by the mini-app
    when the user edits their profile, so both see the same row.
    """
    profile = await get_or_create_profile(db, caller.max_user_id)

    for field in ("status", "region", "industry", "priority"):
        value = getattr(payload, field)
        if value is not None:
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileRead, responses=AUTH_ERRORS)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    caller: Caller = Depends(get_caller),
):
    """The caller's profile, created empty if the dialog hasn't started yet."""
    profile = await get_or_create_profile(db, caller.max_user_id)
    await db.commit()
    await db.refresh(profile)
    return profile
