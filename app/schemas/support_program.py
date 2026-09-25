from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SupportProgramRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    region: Optional[str] = None
    industries: Optional[List[str]] = None
    conditions: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[str] = None
    deadline: Optional[str] = None
    doc_checklist: Optional[List[str]] = None
    source_url: Optional[str] = None
    is_mock: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportProgramMatchRead(SupportProgramRead):
    score: float
    reasons: List[str]
