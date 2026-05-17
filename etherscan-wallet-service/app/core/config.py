from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    etherscan_api_key: str = Field(min_length=1)
    app_port: int = Field(default=8000, ge=1, le=65535)
    etherscan_timeout_seconds: float = Field(default=10, gt=0)
    etherscan_rps_limit: int = Field(default=3, ge=1)
    default_chain_id: int = Field(default=1, gt=0)
    etherscan_retry_attempts: int = Field(default=2, ge=1, le=5)
    etherscan_base_url: str = Field(default="https://api.etherscan.io/v2/api")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
