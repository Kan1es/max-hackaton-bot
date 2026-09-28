from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.options import APPLICATION_STATUS
from app.schemas.support_program import SupportProgramRead


class ApplicationCreate(BaseModel):
    """Save a program into "Мои заявки".

    The profile is resolved from the authenticated caller, so the body only
    names the program.
    """
    program_id: int
    status: str = "saved"

    @field_validator("status")
    @classmethod
    def _check_status(cls, value: str) -> str:
        if value not in APPLICATION_STATUS:
            raise ValueError(f"status must be one of: {', '.join(APPLICATION_STATUS)}")
        return value


class ApplicationUpdate(BaseModel):
    """Partial update: omitted fields are left as they are."""
    status: Optional[str] = None
    checked_docs: Optional[List[str]] = None

    @field_validator("status")
    @classmethod
    def _check_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in APPLICATION_STATUS:
            raise ValueError(f"status must be one of: {', '.join(APPLICATION_STATUS)}")
        return value


class ApplicationRead(BaseModel):
    id: int
    profile_id: int
    program_id: int
    status: str
    checked_docs: List[str] = []
    created_at: datetime
    program: Optional[SupportProgramRead] = None

    model_config = ConfigDict(from_attributes=True)
