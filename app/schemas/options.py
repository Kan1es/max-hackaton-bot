from typing import Dict, List

from pydantic import BaseModel


class OptionsResponse(BaseModel):
    """Canonical dialog options, served so the bot and mini-app never keep
    their own hardcoded copies (app/core/options.py is the source of truth)."""
    status: List[str]
    region: List[str]
    industry: List[str]
    priority: List[str]
    application_status: List[str]
    other_region_label: str
    industry_keywords: Dict[str, List[str]]
