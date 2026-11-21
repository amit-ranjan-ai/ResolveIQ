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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()