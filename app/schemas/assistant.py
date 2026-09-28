from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AssistantTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # Recent turns of the same conversation, oldest first, so follow-ups like
    # "а какие документы для неё?" resolve. The bot keeps them; the API is
    # stateless.
    history: List[AssistantTurn] = Field(default_factory=list, max_length=10)


class AssistantProgramRef(BaseModel):
    id: int
    title: str
    type: Optional[str] = None
    highlight: Optional[str] = None


class AssistantResponse(BaseModel):
    answer: str
    programs: List[AssistantProgramRef]
    # True when the LLM was unavailable and the answer is a keyword search.
    is_stub: bool
