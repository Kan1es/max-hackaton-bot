from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Body of every 4xx the API raises itself (FastAPI's HTTPException)."""
    detail: str


# Declared on endpoints so the published OpenAPI contract lists the error
# codes a client can actually get, not only the 200.
AUTH_ERRORS = {
    401: {"model": ErrorResponse, "description": "Нет или неверная аутентификация"},
    400: {"model": ErrorResponse, "description": "Сервисный токен без X-Max-User-Id"},
}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "Объект не найден"}}
