"""Runtime settings loaded from environment. One Settings per process."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "auth-service"
    service_schema: str = Field(default="auth", alias="SERVICE_SCHEMA")

    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=480, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    seed_manager_phone: str = Field(default="+998901111111", alias="SEED_MANAGER_PHONE")
    seed_manager_password: str = Field(default="manager123", alias="SEED_MANAGER_PASSWORD")
    seed_reception_phone: str = Field(default="+998902222222", alias="SEED_RECEPTION_PHONE")
    seed_reception_password: str = Field(default="reception123", alias="SEED_RECEPTION_PASSWORD")
    seed_technician_phone: str = Field(default="+998903333333", alias="SEED_TECHNICIAN_PHONE")
    seed_technician_password: str = Field(
        default="technician123", alias="SEED_TECHNICIAN_PASSWORD"
    )
    seed_cleaner_phone: str = Field(default="+998904444444", alias="SEED_CLEANER_PHONE")
    seed_cleaner_password: str = Field(default="cleaner123", alias="SEED_CLEANER_PASSWORD")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
