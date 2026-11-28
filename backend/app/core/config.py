from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "ResolveIQ"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "resolveiq_db"
    DB_USER: str = "resolveiq_app"
    DB_PASSWORD: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    UPLOAD_DIRECTORY: Path = Path("uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    VALKEY_URL: str = "valkey://127.0.0.1:6379/0"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_TIMEOUT_SECONDS: int = 60
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
