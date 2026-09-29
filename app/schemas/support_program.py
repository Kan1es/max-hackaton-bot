from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SupportProgramRead(BaseModel):
    id: int
    name: str
    # Short marketing-style name for list cards; falls back to `name` in the UI.
    short_title: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    industries: Optional[List[str]] = None
    eligible_status: Optional[str] = None
    conditions: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[str] = None
    highlight: Optional[str] = None
    deadline: Optional[str] = None
    doc_checklist: Optional[List[str]] = None
    source_url: Optional[str] = None
    checked_at: Optional[str] = None
    is_mock: bool
    # Official portal the program was collected from; None for demo data.
    source: Optional[str] = None
    ends_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportProgramMatchRead(SupportProgramRead):
    score: float
    reasons: List[str]
