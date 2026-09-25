from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    id: int
    max_user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
