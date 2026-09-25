from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProfileUpsert(BaseModel):
    """Payload the bot sends after every answered dialog step (partial upsert)."""
    max_user_id: int
    status: Optional[str] = None
    region: Optional[str] = None
    industry: Optional[str] = None
    priority: Optional[str] = None


class ProfileRead(BaseModel):
    id: int
    user_id: int
    status: Optional[str] = None
    region: Optional[str] = None
    industry: Optional[str] = None
    priority: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
