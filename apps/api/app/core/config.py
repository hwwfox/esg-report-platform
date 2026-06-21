from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    app_name: str = "esg-report-platform"
    app_port: int = 8080
    database_url: str = "postgresql+psycopg://esg_user:esg_password@localhost:5432/esg_dev"
    redis_url: str = "redis://localhost:6379/0"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "minioadmin"
    jwt_secret: str = "local_dev_jwt_secret_change_me"
    ai_provider: str = "mock"
    ai_api_base_url: str = "http://localhost:9002"
    log_level: str = "DEBUG"
    cors_allowed_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file="../../.env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
