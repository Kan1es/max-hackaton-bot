from typing import Any, Optional

import httpx

from bot.config import settings


class BackendClient:
    """Thin async wrapper around the FastAPI backend consumed by the dialog."""

    def __init__(self, base_url: str = settings.BACKEND_BASE_URL):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=10.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def upsert_profile(self, max_user_id: int, **fields: Any) -> dict:
        payload = {"max_user_id": max_user_id, **{k: v for k, v in fields.items() if v is not None}}
        response = await self._client.post("/profile/", json=payload)
        response.raise_for_status()
        return response.json()

    async def match_programs(self, profile_id: int) -> list[dict]:
        response = await self._client.get(f"/programs/match/{profile_id}")
        response.raise_for_status()
        return response.json()

    async def save_application(self, profile_id: int, program_id: int) -> dict:
        response = await self._client.post(
            "/applications/", json={"profile_id": profile_id, "program_id": program_id}
        )
        response.raise_for_status()
        return response.json()

    async def classify_industry(self, text: str) -> tuple[Optional[str], float]:
        response = await self._client.post("/classify/", json={"text": text})
        response.raise_for_status()
        data = response.json()
        return data.get("industry"), data.get("confidence", 0.0)


backend = BackendClient()
