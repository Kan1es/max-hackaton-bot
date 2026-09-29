"""Caller authentication.

Three ways a request can identify itself, checked in this order:

1. `Authorization: tma <initData>` — the raw, *unmodified* `WebApp.initData`
   string from the MAX mini-app. Verified with an HMAC-SHA256 signature keyed
   on the bot token, the same scheme MAX documents for mini-app auth. Never
   trust `initDataUnsafe` from the client instead of this.
2. `X-Service-Token` + `X-Max-User-Id` — server-to-server calls from the bot,
   which runs on our own infrastructure and has no browser signature to pass.
3. `X-Max-User-Id` alone — accepted only when REQUIRE_SIGNED_INIT_DATA=False,
   so Swagger/curl stay usable in local development.

Without one of these the request is rejected: every profile-scoped endpoint
derives the user from here rather than from a body field or a path id, which
is what stops one user from reading or overwriting another user's data.
"""
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, status

from app.core.config import settings


class InitDataError(ValueError):
    """Raised when an initData string is malformed, unsigned or expired."""


@dataclass(frozen=True)
class Caller:
    max_user_id: int
    # True when the identity came from a verified signature or the service
    # token; False only in the unsigned development fallback.
    verified: bool


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def verify_init_data(init_data: str, bot_token: str, max_age: int) -> dict:
    """Validate a mini-app initData string and return its parsed fields."""
    if not bot_token:
        raise InitDataError("MAX_BOT_TOKEN is not configured on the server")

    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    if not pairs:
        raise InitDataError("initData is empty or not a query string")

    fields = dict(pairs)
    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise InitDataError("initData has no hash field")

    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    expected = hmac.new(
        _secret_key(bot_token), check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("initData signature does not match")

    auth_date = fields.get("auth_date")
    if max_age and auth_date:
        try:
            issued_at = int(auth_date)
        except ValueError as exc:
            raise InitDataError("initData auth_date is not a timestamp") from exc
        if time.time() - issued_at > max_age:
            raise InitDataError("initData has expired")

    return fields


def _user_id_from_init_data(fields: dict) -> int:
    raw_user = fields.get("user")
    if not raw_user:
        raise InitDataError("initData has no user field")
    try:
        user_id = json.loads(raw_user)["id"]
        return int(user_id)
    except (ValueError, KeyError, TypeError) as exc:
        raise InitDataError("initData user field is malformed") from exc


async def get_caller(
    authorization: Optional[str] = Header(
        default=None,
        description="`tma <WebApp.initData>` — подписанные данные запуска mini app",
    ),
    x_service_token: Optional[str] = Header(
        default=None,
        description="Сервисный токен (SERVICE_TOKEN) для вызовов бота и проверки жюри",
    ),
    x_max_user_id: Optional[int] = Header(
        default=None,
        description="ID пользователя MAX; вместе с X-Service-Token",
    ),
) -> Caller:
    """FastAPI dependency resolving the authenticated MAX user."""
    if authorization and authorization.lower().startswith("tma "):
        try:
            fields = verify_init_data(
                authorization[4:].strip(),
                settings.MAX_BOT_TOKEN,
                settings.INIT_DATA_MAX_AGE,
            )
            return Caller(max_user_id=_user_id_from_init_data(fields), verified=True)
        except InitDataError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
            ) from exc

    if x_service_token:
        if not settings.SERVICE_TOKEN or not hmac.compare_digest(
            x_service_token, settings.SERVICE_TOKEN
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token"
            )
        if x_max_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Max-User-Id is required with a service token",
            )
        return Caller(max_user_id=x_max_user_id, verified=True)

    if not settings.REQUIRE_SIGNED_INIT_DATA and x_max_user_id is not None:
        return Caller(max_user_id=x_max_user_id, verified=False)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: pass `Authorization: tma <initData>`",
        headers={"WWW-Authenticate": "tma"},
    )
