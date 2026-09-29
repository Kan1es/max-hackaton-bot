from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.profiles import get_or_create_profile
from app.core.database import get_db
from app.core.security import Caller, get_caller
from app.models.match import Match
from app.models.support_program import SupportProgram
from app.schemas.support_program import SupportProgramMatchRead, SupportProgramRead
from app.schemas.error import AUTH_ERRORS, NOT_FOUND
from app.services.catalog import active_programs
from app.services.matching import TOP_N, rank_programs

router = APIRouter(prefix="/programs", tags=["Programs"])


@router.get("/", response_model=list[SupportProgramRead])
async def list_programs(db: AsyncSession = Depends(get_db)):
    """Full catalog. Public: it contains no user data."""
    result = await db.execute(active_programs().order_by(SupportProgram.id))
    return result.scalars().all()


@router.get("/match/me", response_model=list[SupportProgramMatchRead], responses=AUTH_ERRORS)
async def match_programs(
    limit: int = Query(default=TOP_N, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    caller: Caller = Depends(get_caller),
):
    """Rule-based ranking for the caller (region + industry + priority + status).

    `limit` lets the mini-app's catalog show the whole ranked list while the
    bot and the home screen take the default top-3. Only the top-3 snapshot is
    mirrored into `matches`, and it is upserted rather than appended, so
    repeating this request — which the mini-app does on every open — neither
    piles up duplicate rows nor inflates the analytics table.
    """
    profile = await get_or_create_profile(db, caller.max_user_id)

    result = await db.execute(active_programs())
    scored = rank_programs(profile, result.scalars().all(), limit=limit)

    snapshot = scored[:TOP_N]
    scores = {item.program.id: item.score for item in snapshot}

    result = await db.execute(select(Match).where(Match.profile_id == profile.id))
    stored = {match.program_id: match for match in result.scalars().all()}

    for program_id, match in stored.items():
        if program_id in scores:
            match.score = scores[program_id]
        else:
            await db.delete(match)
    for program_id, score in scores.items():
        if program_id not in stored:
            db.add(Match(profile_id=profile.id, program_id=program_id, score=score))
    await db.commit()

    return [
        SupportProgramMatchRead(
            **SupportProgramRead.model_validate(item.program).model_dump(),
            score=item.score,
            reasons=item.reasons,
        )
        for item in scored
    ]


@router.get("/{program_id}", response_model=SupportProgramRead, responses=NOT_FOUND)
async def get_program(program_id: int, db: AsyncSession = Depends(get_db)):
    program = await db.get(SupportProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return program
