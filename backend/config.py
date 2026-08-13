"""
Application settings — loaded from .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./recruitment.db"

    # ── Ollama / LLM ─────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"

    # ── JWT Auth ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── File Uploads ──────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:8501"

    # ── External Integrations ─────────────────────────────────────────────
    GOOGLE_WORKSPACE_EMAIL: str = ""
    GOOGLE_WORKSPACE_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
