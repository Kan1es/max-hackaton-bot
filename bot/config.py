from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    MAX_BOT_TOKEN: str = ""
    BACKEND_BASE_URL: str = "http://localhost:8000/api/v1"

    # Webhook mode (production). Leave USE_WEBHOOK=False for long polling,
    # which is simpler for local development and demoing the hackathon MVP.
    USE_WEBHOOK: bool = False
    WEBHOOK_HOST: str = "0.0.0.0"
    WEBHOOK_PORT: int = 8080

    MINIAPP_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = BotSettings()
