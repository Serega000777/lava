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
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
