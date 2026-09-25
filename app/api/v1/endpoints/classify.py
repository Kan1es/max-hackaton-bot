from fastapi import APIRouter

from app.core.options import INDUSTRY_KEYWORDS
from app.schemas.classify import ClassifyRequest, ClassifyResponse

router = APIRouter(prefix="/classify", tags=["Classify"])

# TODO(NLP): replace with the real rubert-tiny2 classifier (see architecture
# doc, "NLP-классификатор" box). This placeholder does keyword matching only
# and deliberately caps confidence below the bot's threshold so the dialog
# always falls back to industry buttons until the real model lands.
_STUB_CONFIDENCE = 0.55


@router.post("/", response_model=ClassifyResponse)
async def classify_industry(payload: ClassifyRequest) -> ClassifyResponse:
    text = payload.text.lower()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return ClassifyResponse(industry=industry, confidence=_STUB_CONFIDENCE)
    return ClassifyResponse(industry=None, confidence=0.0)
