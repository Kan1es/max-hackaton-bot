from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Max Hackathon API"
    VERSION: str = "0.1.0"
    # Debug enables SQL echo and auto-create_all; migrations are the real
    # schema source, so this must stay False outside local experiments.
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Comma-separated list of allowed browser origins for the mini-app;
    # "*" allows any. Kept as a plain string because pydantic-settings parses
    # a list-typed setting as JSON before any validator runs, which makes the
    # natural `CORS_ORIGINS=*` or `a,b` spelling a startup crash.
    CORS_ORIGINS: str = "*"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "hackaton_db"

    DATABASE_URL: Optional[str] = None
    SYNC_DATABASE_URL: Optional[str] = None

    # Shared secret used to verify the `initData` string the MAX mini-app
    # passes to the API (see app/core/security.py). Same token as the bot's.
    MAX_BOT_TOKEN: str = ""
    # When False, requests may identify themselves with a plain max_user_id
    # instead of signed initData. Convenient for curl/Swagger, unsafe in prod.
    REQUIRE_SIGNED_INIT_DATA: bool = True
    # How long a signed initData payload stays valid, in seconds.
    INIT_DATA_MAX_AGE: int = 24 * 60 * 60
    # Shared secret for server-to-server calls (the bot), which cannot produce
    # a browser initData signature. Sent as the X-Service-Token header
    # alongside X-Max-User-Id.
    SERVICE_TOKEN: str = ""

    # LLM on OpenRouter: the /classify industry classifier and the
    # /assistant consultant. An empty key disables both; they fall back to
    # keyword search.
    OPENROUTER_API_KEY: str = ""
    # Comma-separated: the first is preferred, the rest are fallbacks.
    OPENROUTER_MODEL: str = "qwen/qwen3.8-27b:free,nvidia/nemotron-3-super-120b-a12b:free,nvidia/nemotron-3-ultra-550b-a55b:free"
    # Must stay well under the bot's 10s HTTP timeout to the API.
    OPENROUTER_TIMEOUT: float = 6.0
    # The consultant writes a paragraph rather than a label, so it gets a
    # longer budget; the bot waits up to ASSISTANT_TIMEOUT + a margin.
    ASSISTANT_TIMEOUT: float = 25.0

    # Collector of real programs from official portals (python -m app.collector).
    # Russian government sites refuse foreign IPs, so their requests may go
    # through a proxy in Russia, e.g. socks5://ru-tunnel:1080. OpenRouter is
    # always called directly.
    COLLECTOR_PROXY: str = ""
    # Comma-separated adapters to run; see app/collector/sources.
    # msp_rf needs COLLECTOR_PROXY; corpmsp works without.
    COLLECTOR_SOURCES: str = "corpmsp,msp_rf"
    # МСП.РФ queries: regions (as the site names them; "г." is optional),
    # applicant types (self = самозанятый, ip, yur, fiz) and support views
    # (1 Деньги, 2 Обучение, 3 Маркетинг, 4 Консультирование, 8 Имущество…).
    # Federal measures come back in every region and are stored once.
    COLLECTOR_MSP_REGIONS: str = "Москва,Московская область,Краснодарский край,Санкт-Петербург"
    COLLECTOR_MSP_APPLICANTS: str = "self,ip"
    COLLECTOR_MSP_VIEWS: str = "1,2"
    COLLECTOR_INTERVAL_HOURS: float = 24.0
    # Upper bound per source and run, so a first run on a free LLM tier
    # finishes in reasonable time. Unchanged items don't count against the LLM.
    COLLECTOR_MAX_ITEMS: int = 300
    # LLM extractions per run, across sources. The bot shares the account's
    # quota: without credits OpenRouter allows 50 free-model requests a day,
    # so the default leaves 20 for users. With credits (1000/day) raise it.
    COLLECTOR_LLM_BUDGET: int = 30
    # Pause between LLM extractions — free models are rate-limited.
    COLLECTOR_LLM_DELAY: float = 3.0
    COLLECTOR_LLM_TIMEOUT: float = 60.0
    # The demo catalog is hidden once this many real programs are active.
    DEMO_CATALOG_MIN_REAL: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()] or ["*"]

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
