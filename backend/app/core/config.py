from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "AI Banking Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-change-in-production"

    AI_PROVIDER: str = "mock"  # one of: mock | openai_compatible
    AI_API_KEY: str = ""  # server-side only; never exposed to the frontend
    AI_BASE_URL: str = ""  # e.g. https://api.openai.com/v1 (OpenAI-compatible)
    AI_MODEL: str = ""  # model identifier requested from the provider
    AI_TIMEOUT_SECONDS: float = 20.0  # per-call network timeout
    AI_MAX_RETRIES: int = 1  # retries for transient errors (not for 4xx)
    AI_RATE_LIMIT_COOLDOWN: float = 10.0  # seconds to back off after HTTP 429
    AI_MAX_MESSAGE_LENGTH: int = 500  # input sanitisation cap
    AI_HISTORY_TURNS: int = 10  # conversation turns kept in session memory

    DATABASE_URL: str = "sqlite:///./atm_banking.db"
    SESSION_TIMEOUT_MINUTES: int = 30

    # Deployment (Phase 8): when enabled, the built frontend (frontend/dist)
    # is served by FastAPI itself for single-origin kiosk deployments - no
    # CORS/proxying involved. The deterministic backend always stays the sole
    # authority for banking operations; this only mounts static files.
    SERVE_FRONTEND_DIST: bool = False
    FRONTEND_DIST_PATH: str = "../frontend/dist"

    # OCR (Phase 4) - engine selection is centralised here
    TESSERACT_CMD: str = ""  # optional explicit path to tesseract.exe
    OCR_LANGUAGES: str = "eng,hin,tel"  # default language set for documents

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
