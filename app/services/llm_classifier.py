"""Industry classification via an LLM on OpenRouter.

Every failure mode (no key, timeout, rate limit, malformed answer,
industry outside the known list) returns None so the caller can fall back to
the keyword scorer instead of failing the request.
"""
import json
import logging
import re
from typing import Optional, Tuple

from app.core.config import settings
from app.core.options import PROFILE_INDUSTRY
from app.services.openrouter import chat_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты классифицируешь описание бизнеса по отраслям. "
    "Допустимые отрасли: {industries}. "
    'Ответь строго JSON без пояснений: {{"industry": "<одна из отраслей или null>", '
    '"confidence": <число от 0 до 1>}}. '
    "Если текст не описывает бизнес или отрасль неясна, верни industry null."
)

# Reasoning models may wrap the answer in prose or a ```json fence; grab the
# first flat JSON object.
_JSON_OBJECT = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _parse_answer(content: str) -> Optional[Tuple[Optional[str], float]]:
    match = _JSON_OBJECT.search(content or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        confidence = float(data.get("confidence", 0.0))
    except (ValueError, TypeError, AttributeError):
        return None

    industry = data.get("industry")
    if industry in (None, "null", ""):
        return None, 0.0
    if industry not in PROFILE_INDUSTRY:
        return None
    return industry, max(0.0, min(1.0, confidence))


async def classify_with_llm(text: str) -> Optional[Tuple[Optional[str], float]]:
    """Return (industry, confidence), or None when the LLM gave no usable answer."""
    content = await chat_completion(
        [
            {"role": "system", "content": SYSTEM_PROMPT.format(industries=", ".join(PROFILE_INDUSTRY))},
            {"role": "user", "content": text},
        ],
        max_tokens=100,
        timeout=settings.OPENROUTER_TIMEOUT,
    )
    if content is None:
        return None

    result = _parse_answer(content)
    if result is None:
        logger.warning("OpenRouter returned an unusable answer: %.200s", content)
    return result
