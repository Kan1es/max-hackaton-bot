from typing import Optional

from pydantic import BaseModel


class ClassifyRequest(BaseModel):
    text: str


class ClassifyResponse(BaseModel):
    industry: Optional[str] = None
    confidence: float
