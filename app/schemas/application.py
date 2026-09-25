from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.support_program import SupportProgramRead


class ApplicationCreate(BaseModel):
    profile_id: int
    program_id: int
    status: str = "saved"


class ApplicationRead(BaseModel):
    id: int
    profile_id: int
    program_id: int
    status: str
    created_at: datetime
    program: Optional[SupportProgramRead] = None

    model_config = ConfigDict(from_attributes=True)
