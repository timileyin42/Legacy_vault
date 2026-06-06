from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Eterna"
    environment: str = "local"
    debug: bool = False
    database_url: str = "sqlite:///./eterna.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = Field(default="local-only-change-me")
    encryption_key: str = Field(default="local-only-change-me")
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    jwt_algorithm: str = "HS256"
    allowed_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    mfa_issuer: str = "Eterna"
    storage_provider: str = "cloudflare_r2"
    cloudflare_r2_account_id: str | None = None
    cloudflare_r2_access_key_id: str | None = None
    cloudflare_r2_secret_access_key: str | None = None
    cloudflare_r2_bucket_name: str | None = None
    cloudflare_r2_public_base_url: str | None = None
    cloudflare_r2_presigned_url_expire_seconds: int = 900
    resend_api_key: str | None = None
    resend_from_email: str = "Eterna Security <security@example.com>"
    fcm_server_key: str | None = None  # Deprecated legacy FCM key; retained for back-compat only.
    fcm_service_account_base64: str | None = None  # Base64-encoded Firebase service-account JSON (FCM HTTP v1).
    firebase_project_id: str | None = None
    email_verification_code_ttl_minutes: int = 10
    paystack_secret_key: str | None = None
    paystack_public_key: str | None = None
    paystack_currency: str = "NGN"
    paystack_callback_url: str | None = None
    sentry_dsn: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> bool:
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return bool(value) if isinstance(value, bool) else value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production:
        if settings.secret_key.startswith("change-me") or settings.secret_key == "local-only-change-me":
            raise ValueError("SECRET_KEY must be configured for production.")
        if settings.encryption_key.startswith("change-me") or settings.encryption_key == "local-only-change-me":
            raise ValueError("ENCRYPTION_KEY must be configured for production.")
    return settings
