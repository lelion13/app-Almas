from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Almas API"
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/almas",
        validation_alias="DATABASE_URL",
    )
    jwt_secret: str = Field(
        default="change-me-in-production-use-long-random-secret",
        validation_alias="JWT_SECRET",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_bytes: int = 10 * 1024 * 1024
    timezone_local: str = "America/Argentina/Buenos_Aires"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}


settings = Settings()
