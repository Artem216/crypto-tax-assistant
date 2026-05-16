"""Schemas for ETH/USD enrichment endpoints."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TransactionPayload(BaseModel):
    """Input transaction with arbitrary passthrough fields."""

    tx_hash: str = Field(min_length=1)
    timestamp: Any

    model_config = ConfigDict(extra="allow")

    @field_validator("tx_hash")
    @classmethod
    def normalize_tx_hash(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("tx_hash must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_timestamp_presence(self) -> "TransactionPayload":
        if self.timestamp is None:
            raise ValueError("timestamp is required")
        return self


class EnrichTransactionsRequest(BaseModel):
    transactions: list[TransactionPayload] = Field(min_length=1)


class PricingPayload(BaseModel):
    pricing_date_utc: date
    eth_usd: float
    coin_id: Literal["ethereum"] = "ethereum"
    source: Literal["coingecko"] = "coingecko"


class EnrichedTransaction(BaseModel):
    tx_hash: str
    timestamp: Any
    pricing: PricingPayload

    model_config = ConfigDict(extra="allow")


class EnrichTransactionsResponse(BaseModel):
    asset: Literal["ETH"] = "ETH"
    quote_currency: Literal["USD"] = "USD"
    items: list[EnrichedTransaction]
