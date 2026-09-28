from fastapi import APIRouter, Depends

from app.core.options import INDUSTRY_KEYWORDS
from app.core.security import Caller, get_caller
from app.schemas.classify import ClassifyRequest, ClassifyResponse
from app.services.llm_classifier import classify_with_llm

router = APIRouter(prefix="/classify", tags=["Classify"])

# The LLM (OpenRouter) answers first; when it is unconfigured or fails, a
# keyword scorer takes over: confidence grows with the number of distinct industry
# terms found, so a single incidental hit stays below the bot's threshold
# while a clearly-worded answer ("пеку торты на заказ, продаю через интернет")
# clears it.
BASE_CONFIDENCE = 0.55
CONFIDENCE_PER_HIT = 0.1
MAX_CONFIDENCE = 0.9


@router.post("/", response_model=ClassifyResponse)
async def classify_industry(
    payload: ClassifyRequest,
    caller: Caller = Depends(get_caller),
) -> ClassifyResponse:
    llm_result = await classify_with_llm(payload.text)
    if llm_result is not None:
        industry, confidence = llm_result
        return ClassifyResponse(industry=industry, confidence=confidence, is_stub=False)

    text = payload.text.lower()

    best_industry, best_hits = None, 0
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in text)
        if hits > best_hits:
            best_industry, best_hits = industry, hits

    if not best_industry:
        return ClassifyResponse(industry=None, confidence=0.0, is_stub=True)

    confidence = min(MAX_CONFIDENCE, BASE_CONFIDENCE + CONFIDENCE_PER_HIT * best_hits)
    return ClassifyResponse(industry=best_industry, confidence=confidence, is_stub=True)
