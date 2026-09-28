from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    MAX_BOT_TOKEN: str = ""
    BACKEND_BASE_URL: str = "http://localhost:8000/api/v1"

    # Shared secret for server-to-server calls. The bot has no browser
    # initData to sign, so it authenticates with this plus X-Max-User-Id.
    SERVICE_TOKEN: str = ""

    # Webhook mode (production). Leave USE_WEBHOOK=False for long polling,
    # which is simpler for local development and demoing the hackathon MVP.
    USE_WEBHOOK: bool = False
    WEBHOOK_HOST: str = "0.0.0.0"
    WEBHOOK_PORT: int = 8080

    # Public HTTPS address of the mini-app. Used as a plain-link fallback when
    # the bot cannot resolve its own username for the native "open app" button.
    MINIAPP_URL: str = ""

    # Minimum confidence before the free-text industry answer is accepted
    # without asking the user to confirm with a button.
    CLASSIFY_CONFIDENCE_THRESHOLD: float = 0.6

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = BotSettings()
