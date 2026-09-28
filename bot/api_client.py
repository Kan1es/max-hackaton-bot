"""Async wrapper around the FastAPI backend.

Every profile-scoped call is authenticated as a specific MAX user with the
service token + X-Max-User-Id pair: the backend resolves the profile from
those headers, so the bot never passes a profile id around and can never act
on the wrong person's data by getting an id wrong.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from bot.config import settings
from bot.options import DialogOptions

logger = logging.getLogger("bot.api_client")

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
# The AI consultant retries a rate-limited free model inside its own budget
# (ASSISTANT_TIMEOUT on the backend), so the bot waits a little longer.
ASSISTANT_TIMEOUT = httpx.Timeout(40.0, connect=5.0)


class BackendError(RuntimeError):
    """The backend was unreachable or answered with an error status."""


class BackendClient:
    def __init__(self, base_url: str = settings.BACKEND_BASE_URL):
        headers = {"Accept": "application/json"}
        if settings.SERVICE_TOKEN:
            headers["X-Service-Token"] = settings.SERVICE_TOKEN
        self._client = httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT, headers=headers)

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _as_user(max_user_id: int) -> Dict[str, str]:
        return {"X-Max-User-Id": str(max_user_id)}

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Backend %s %s -> %s: %s",
                method, url, exc.response.status_code, exc.response.text[:400],
            )
            raise BackendError(f"{method} {url} failed: {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            logger.error("Backend %s %s unreachable: %s", method, url, exc)
            raise BackendError(f"{method} {url} unreachable") from exc

    # --- startup -------------------------------------------------------
    async def load_options(self, attempts: int = 10, delay: float = 2.0) -> DialogOptions:
        """Fetch the canonical dialog options, retrying while the API boots.

        docker-compose already waits for the backend's healthcheck, but a bot
        started by hand may well come up first — better to wait than to crash
        into a restart loop.
        """
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                response = await self._request("GET", "/options/")
                return DialogOptions.from_api(response.json())
            except BackendError as exc:
                last_error = exc
                logger.warning("Опции недоступны (попытка %s/%s), жду...", attempt, attempts)
                await asyncio.sleep(delay)
        raise BackendError(f"Не удалось загрузить опции диалога: {last_error}")

    # --- profile-scoped calls -------------------------------------------
    async def upsert_profile(self, max_user_id: int, **fields: Any) -> dict:
        payload = {k: v for k, v in fields.items() if v is not None}
        response = await self._request(
            "POST", "/profile/", json=payload, headers=self._as_user(max_user_id)
        )
        return response.json()

    async def match_programs(self, max_user_id: int) -> List[dict]:
        response = await self._request(
            "GET", "/programs/match/me", headers=self._as_user(max_user_id)
        )
        return response.json()

    async def save_application(self, max_user_id: int, program_id: int) -> dict:
        response = await self._request(
            "POST", "/applications/",
            json={"program_id": program_id},
            headers=self._as_user(max_user_id),
        )
        return response.json()

    async def classify_industry(self, max_user_id: int, text: str) -> Tuple[Optional[str], float]:
        response = await self._request(
            "POST", "/classify/", json={"text": text}, headers=self._as_user(max_user_id)
        )
        data = response.json()
        return data.get("industry"), data.get("confidence", 0.0)

    async def list_applications(self, max_user_id: int) -> List[dict]:
        response = await self._request(
            "GET", "/applications/", headers=self._as_user(max_user_id)
        )
        return response.json()

    async def ask_assistant(
        self, max_user_id: int, question: str, history: List[Dict[str, str]]
    ) -> dict:
        response = await self._request(
            "POST", "/assistant/ask",
            json={"question": question, "history": history},
            headers=self._as_user(max_user_id),
            timeout=ASSISTANT_TIMEOUT,
        )
        return response.json()

    # --- public catalog ---------------------------------------------------
    async def get_program(self, program_id: int) -> dict:
        response = await self._request("GET", f"/programs/{program_id}")
        return response.json()


backend = BackendClient()
