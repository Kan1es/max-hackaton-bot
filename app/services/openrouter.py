"""Minimal OpenRouter chat-completions client shared by every LLM feature.

OpenRouter speaks the OpenAI protocol, so one POST is enough. Every failure
(no key, timeout, rate limit, malformed body) returns None: callers always
have a non-LLM fallback and must never fail a request because of the model.
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free models are rate-limited from a shared upstream pool and 429s come and
# go within seconds, so retrying inside the caller's time budget recovers a
# good share of them. The delay grows with each attempt.
RATE_LIMIT_RETRY_DELAY = 1.5
MAX_ATTEMPTS = 4


# Epoch seconds until which the account's daily quota of free-model requests
# is used up (50/day without credits). Until then every call would be a 429,
# so none is made — retrying only burns time the user is waiting through.
_daily_quota_reset = 0.0


def daily_quota_exhausted() -> bool:
    return time.time() < _daily_quota_reset


def _note_daily_quota(response: httpx.Response) -> bool:
    """True (and remembered) if this 429 is the per-day quota, not a busy pool."""
    global _daily_quota_reset
    if "free-models-per-day" not in response.text:
        return False
    try:
        headers = response.json()["error"]["metadata"]["headers"]
        reset = float(headers["X-RateLimit-Reset"]) / 1000
    except (ValueError, KeyError, TypeError):
        reset = time.time() + 3600
    _daily_quota_reset = max(reset, time.time() + 60)
    logger.warning("OpenRouter daily free-model quota is used up until %s",
                   time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(_daily_quota_reset)))
    return True


def configured_models() -> List[str]:
    return [m.strip() for m in settings.OPENROUTER_MODEL.split(",") if m.strip()]


def is_enabled() -> bool:
    return bool(settings.OPENROUTER_API_KEY and configured_models())


async def chat_completion(
    messages: List[Dict[str, str]],
    *,
    max_tokens: int,
    timeout: float,
    temperature: float = 0.0,
) -> Optional[str]:
    """Return the assistant message text, or None when there is no usable answer."""
    models = configured_models()
    if not settings.OPENROUTER_API_KEY or not models or daily_quota_exhausted():
        return None

    payload = {
        # A comma-separated OPENROUTER_MODEL becomes OpenRouter's fallback
        # list: the router moves on to the next model by itself.
        "model": models[0],
        "models": models,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # Qwen3 thinks before answering by default. Reasoning tokens count
        # against max_tokens, so a short budget used to come back with an
        # empty content — and thinking also triples the latency.
        "reasoning": {"enabled": False},
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "X-Title": settings.PROJECT_NAME,
    }

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    async with httpx.AsyncClient() as client:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            remaining = deadline - loop.time()
            if remaining <= 0.5:
                break
            try:
                response = await client.post(
                    OPENROUTER_URL, json=payload, headers=headers, timeout=remaining
                )
                if response.status_code == 429 and _note_daily_quota(response):
                    return None
                if response.status_code == 429 and attempt < MAX_ATTEMPTS:
                    delay = RATE_LIMIT_RETRY_DELAY * attempt
                    if deadline - loop.time() - delay < 2:
                        logger.info("OpenRouter rate-limited, no time left to retry")
                        return None
                    logger.info("OpenRouter rate-limited, retry %s in %.1fs", attempt, delay)
                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                logger.warning("OpenRouter request failed: %r", exc)
                return None
            return content.strip() if isinstance(content, str) and content.strip() else None
    logger.warning("OpenRouter gave no answer within %.1fs", timeout)
    return None
