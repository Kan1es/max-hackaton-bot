from fastapi import APIRouter

from app.core import options as canonical
from app.schemas.options import OptionsResponse

router = APIRouter(prefix="/options", tags=["Options"])


@router.get("/", response_model=OptionsResponse)
async def get_options() -> OptionsResponse:
    """Canonical dialog options.

    The bot loads this at startup to build its keyboards and the mini-app
    loads it to build its dropdowns, so neither keeps a hardcoded copy that
    can drift from app/core/options.py.
    """
    return OptionsResponse(
        status=canonical.PROFILE_STATUS,
        region=canonical.PROFILE_REGION,
        industry=canonical.PROFILE_INDUSTRY,
        priority=canonical.PROFILE_PRIORITY,
        application_status=canonical.APPLICATION_STATUS,
        other_region_label=canonical.OTHER_REGION_LABEL,
        industry_keywords=canonical.INDUSTRY_KEYWORDS,
    )
