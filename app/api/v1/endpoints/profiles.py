from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileRead, ProfileUpsert

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post("/", response_model=ProfileRead)
async def upsert_profile(payload: ProfileUpsert, db: AsyncSession = Depends(get_db)):
    """Create or partially update a profile, keyed by the MAX user id.

    Called by the bot after every answered dialog step, so the profile in
    Postgres is always in sync with what the user has told the bot so far.
    """
    result = await db.execute(select(User).where(User.max_user_id == payload.max_user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(max_user_id=payload.max_user_id)
        db.add(user)
        await db.flush()

    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)

    for field in ("status", "region", "industry", "priority"):
        value = getattr(payload, field)
        if value is not None:
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/by-max-user/{max_user_id}", response_model=ProfileRead)
async def get_profile_by_max_user(max_user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.max_user_id == max_user_id))
    user = result.scalar_one_or_none()
    profile = None
    if user is not None:
        result = await db.execute(select(Profile).where(Profile.user_id == user.id))
        profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
