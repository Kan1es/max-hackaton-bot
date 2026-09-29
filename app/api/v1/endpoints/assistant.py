from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.profiles import get_or_create_profile
from app.core.database import get_db
from app.core.security import Caller, get_caller
from app.models.support_program import SupportProgram
from app.schemas.assistant import AssistantProgramRef, AssistantRequest, AssistantResponse
from app.schemas.error import AUTH_ERRORS
from app.services.assistant import HistoryTurn, answer_question
from app.services.catalog import active_programs

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/ask", response_model=AssistantResponse, responses=AUTH_ERRORS)
async def ask_assistant(
    payload: AssistantRequest,
    db: AsyncSession = Depends(get_db),
    caller: Caller = Depends(get_caller),
) -> AssistantResponse:
    """Answer a free-form question from the catalog, tailored to the caller's profile."""
    profile = await get_or_create_profile(db, caller.max_user_id)
    await db.commit()

    result = await db.execute(active_programs().order_by(SupportProgram.id))
    programs = result.scalars().all()

    answer = await answer_question(
        payload.question,
        profile,
        programs,
        history=[HistoryTurn(role=t.role, content=t.content) for t in payload.history],
    )

    by_id = {p.id: p for p in programs}
    return AssistantResponse(
        answer=answer.text,
        programs=[
            AssistantProgramRef(
                id=pid,
                title=by_id[pid].short_title or by_id[pid].name,
                type=by_id[pid].type,
                highlight=by_id[pid].highlight,
            )
            for pid in answer.program_ids
        ],
        is_stub=answer.is_stub,
    )
