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

    mp_client_id: str = Field(default="", validation_alias="MP_CLIENT_ID")
    mp_client_secret: str = Field(default="", validation_alias="MP_CLIENT_SECRET")
    mp_redirect_uri: str = Field(default="", validation_alias="MP_REDIRECT_URI")
    mp_token_encryption_key: str = Field(default="", validation_alias="MP_TOKEN_ENCRYPTION_KEY")
    mp_api_base_url: str = Field(default="https://api.mercadopago.com", validation_alias="MP_API_BASE_URL")
    mp_auth_base_url: str = Field(default="https://auth.mercadopago.com", validation_alias="MP_AUTH_BASE_URL")
    mp_api_timeout_seconds: int = Field(default=20, validation_alias="MP_API_TIMEOUT_SECONDS")
    mp_report_poll_interval_seconds: float = Field(
        default=2.0, validation_alias="MP_REPORT_POLL_INTERVAL_SECONDS"
    )
    mp_report_poll_timeout_seconds: float = Field(
        default=120.0, validation_alias="MP_REPORT_POLL_TIMEOUT_SECONDS"
    )
    mp_oauth_frontend_redirect: str = Field(
        default="http://localhost:5173/conciliacion",
        validation_alias="MP_OAUTH_FRONTEND_REDIRECT",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}


settings = Settings()
