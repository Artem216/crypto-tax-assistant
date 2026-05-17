"""Application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


CoinGeckoApiTier = Literal["public", "demo", "pro"]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_port: int = Field(default=8000, ge=1, le=65535)
    coingecko_api_tier: CoinGeckoApiTier = "public"
    coingecko_api_key: str | None = None
    coingecko_timeout_seconds: float = Field(default=10.0, gt=0)
    coingecko_rps_limit: int = Field(default=3, ge=1)
    coingecko_retry_attempts: int = Field(default=2, ge=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_api_key_requirements(self) -> "Settings":
        if self.coingecko_api_tier in {"demo", "pro"} and not self.coingecko_api_key:
            raise ValueError(
                "COINGECKO_API_KEY is required when COINGECKO_API_TIER is demo or pro."
            )
        return self

    @property
    def coingecko_base_url(self) -> str:
        if self.coingecko_api_tier == "pro":
            return "https://pro-api.coingecko.com/api/v3"
        return "https://api.coingecko.com/api/v3"

    @property
    def coingecko_api_header_name(self) -> str | None:
        if self.coingecko_api_tier == "demo":
            return "x-cg-demo-api-key"
        if self.coingecko_api_tier == "pro":
            return "x-cg-pro-api-key"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
