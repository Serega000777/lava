from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://lava:lava_local@localhost:5433/lava"
    redis_url: str = "redis://localhost:6380/0"
    session_ttl_hours: int = 720
    password_login_enabled: bool = True
    local_otp_enabled: bool = True
    sms_otp_enabled: bool = False
    vk_oauth_enabled: bool = False
    allowed_origins: str = "http://localhost:3000"
    auth_rate_limit: int = 20
    auth_rate_window_seconds: int = 60
    otp_max_attempts: int = 5
    complaint_rate_limit: int = 10
    complaint_target_rate_limit: int = 3
    complaint_rate_window_seconds: int = 86_400
    message_rate_limit: int = 60
    message_conversation_rate_limit: int = 20
    message_rate_window_seconds: int = 60
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "lava"
    s3_secret_key: str = "lava_local_secret"
    s3_bucket: str = "media"
    media_max_bytes: int = 10 * 1024 * 1024
    media_max_per_listing: int = 10
    media_max_pixels: int = 20_000_000
    metrics_token: SecretStr | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("metrics_token", mode="before")
    @classmethod
    def validate_metrics_token(cls, value: object) -> object:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if raw == "":
            return None
        if isinstance(raw, str) and len(raw) < 32:
            raise ValueError("metrics_token must contain at least 32 characters")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
