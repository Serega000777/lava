from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://lava:lava_local@localhost:5433/lava"
    redis_url: str = "redis://localhost:6380/0"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

