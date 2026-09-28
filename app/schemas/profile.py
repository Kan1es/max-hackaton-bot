from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.options import (
    OTHER_REGION_LABEL,
    PROFILE_INDUSTRY,
    PROFILE_PRIORITY,
    PROFILE_STATUS,
)


class ProfileUpsert(BaseModel):
    """Payload sent after every answered dialog step (partial upsert).

    The user is taken from the authenticated caller, never from the body —
    see app/core/security.py. `region` is free text because the dialog lets
    people type a region that isn't on the button list; the other three are
    restricted to the canonical options.
    """
    status: Optional[str] = None
    region: Optional[str] = None
    industry: Optional[str] = None
    priority: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _check_status(cls, value: Optional[str]) -> Optional[str]:
        return _one_of(value, PROFILE_STATUS, "status")

    @field_validator("industry")
    @classmethod
    def _check_industry(cls, value: Optional[str]) -> Optional[str]:
        return _one_of(value, PROFILE_INDUSTRY, "industry")

    @field_validator("priority")
    @classmethod
    def _check_priority(cls, value: Optional[str]) -> Optional[str]:
        return _one_of(value, PROFILE_PRIORITY, "priority")

    @field_validator("region")
    @classmethod
    def _check_region(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("region must not be blank")
        if value == OTHER_REGION_LABEL:
            raise ValueError(
                f"«{OTHER_REGION_LABEL}» is a UI placeholder — send the actual region name"
            )
        return value


def _one_of(value: Optional[str], allowed: list[str], field: str) -> Optional[str]:
    if value is None:
        return None
    if value not in allowed:
        raise ValueError(f"{field} must be one of: {', '.join(allowed)}")
    return value


class ProfileRead(BaseModel):
    id: int
    user_id: int
    status: Optional[str] = None
    region: Optional[str] = None
    industry: Optional[str] = None
    priority: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @property
    def is_complete(self) -> bool:
        return all([self.status, self.region, self.industry, self.priority])

    model_config = ConfigDict(from_attributes=True)
