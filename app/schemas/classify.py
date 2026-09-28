from typing import Optional

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ClassifyResponse(BaseModel):
    industry: Optional[str] = None
    confidence: float
    # True when the answer came from the keyword fallback rather than the
    # LLM, so clients can label or discount it.
    is_stub: bool = True
