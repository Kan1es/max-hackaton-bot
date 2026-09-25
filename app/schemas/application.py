from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class ApplicationBase(BaseModel):
    program_id: int
    status: str = "draft"
    applicant_data: Optional[Dict[str, Any]] = None
    reviewer_notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    user_id: int


class ApplicationRead(ApplicationBase):
    id: int
    user_id: int
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
