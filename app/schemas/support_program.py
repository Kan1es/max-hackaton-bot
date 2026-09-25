from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class SupportProgramBase(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None
    category: str
    provider: Optional[str] = None
    eligibility_criteria: Optional[Dict[str, Any]] = None
    financial_benefit: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    is_active: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SupportProgramCreate(SupportProgramBase):
    pass


class SupportProgramRead(SupportProgramBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
