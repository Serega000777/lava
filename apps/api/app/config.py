from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_RATE_LIMIT_KEY_SECRET = "lava-local-rate-limit-key-change-before-production"


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
    auth_account_failure_window_seconds: int = Field(default=3_600, ge=60, le=86_400)
    auth_account_delay_after: int = Field(default=3, ge=2, le=10)
    auth_account_delay_base_seconds: int = Field(default=2, ge=1, le=60)
    auth_account_delay_max_seconds: int = Field(default=300, ge=10, le=3_600)
    rate_limit_key_secret: SecretStr = SecretStr(LOCAL_RATE_LIMIT_KEY_SECRET)
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
    message_media_max_bytes: int = 5 * 1024 * 1024
    message_media_max_per_message: int = 3
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

    @field_validator("rate_limit_key_secret", mode="before")
    @classmethod
    def validate_rate_limit_key_secret(cls, value: object) -> object:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if not isinstance(raw, str) or len(raw) < 32:
            raise ValueError("rate_limit_key_secret must contain at least 32 characters")
        return value

    @field_validator("message_media_max_per_message")
    @classmethod
    def validate_message_media_limit(cls, value: int) -> int:
        if not 1 <= value <= 3:
            raise ValueError("message_media_max_per_message must be between 1 and 3")
        return value

    @model_validator(mode="after")
    def validate_auth_account_delay_range(self):
        if self.auth_account_delay_max_seconds < self.auth_account_delay_base_seconds:
            raise ValueError(
                "auth_account_delay_max_seconds must be at least the base delay"
            )
        rate_key_secret = self.rate_limit_key_secret.get_secret_value()
        if self.app_env == "production" and (
            rate_key_secret == LOCAL_RATE_LIMIT_KEY_SECRET
            or rate_key_secret.startswith("replace-")
        ):
            raise ValueError("production requires a unique rate_limit_key_secret")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
