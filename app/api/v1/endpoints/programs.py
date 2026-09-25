from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.match import Match
from app.models.profile import Profile
from app.models.support_program import SupportProgram
from app.schemas.support_program import SupportProgramMatchRead, SupportProgramRead
from app.services.matching import rank_programs

router = APIRouter(prefix="/programs", tags=["Programs"])


@router.get("/", response_model=list[SupportProgramRead])
async def list_programs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SupportProgram))
    return result.scalars().all()


@router.get("/match/{profile_id}", response_model=list[SupportProgramMatchRead])
async def match_programs(profile_id: int, db: AsyncSession = Depends(get_db)):
    """Rule-based top-3 matching for a profile (region + industry + priority).

    Persists the results into `matches` for history/analytics, then returns
    them enriched with score and human-readable reasons.
    """
    profile = await db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await db.execute(select(SupportProgram))
    programs = result.scalars().all()

    scored = rank_programs(profile, programs)

    for item in scored:
        db.add(Match(profile_id=profile.id, program_id=item.program.id, score=item.score))
    if scored:
        await db.commit()

    return [
        SupportProgramMatchRead(
            **SupportProgramRead.model_validate(item.program).model_dump(),
            score=item.score,
            reasons=item.reasons,
        )
        for item in scored
    ]


@router.get("/{program_id}", response_model=SupportProgramRead)
async def get_program(program_id: int, db: AsyncSession = Depends(get_db)):
    program = await db.get(SupportProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return program
