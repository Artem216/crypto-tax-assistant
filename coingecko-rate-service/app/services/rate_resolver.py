"""Transaction enrichment logic."""

from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable

from app.clients.coingecko import CoinGeckoClient
from app.core.config import Settings
from app.core.errors import InvalidTransactionPayload
from app.schemas.rates import (
    EnrichTransactionsRequest,
    EnrichTransactionsResponse,
    PricingPayload,
    TransactionPayload,
)


class HistoricalRateResolver:
    """Resolves daily ETH/USD rates and merges them into transactions."""

    def __init__(
        self,
        client: CoinGeckoClient,
        settings: Settings,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._settings = settings
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    async def enrich_transactions(
        self, payload: EnrichTransactionsRequest
    ) -> EnrichTransactionsResponse:
        normalized_transactions: list[tuple[TransactionPayload, date]] = []
        unique_dates: dict[date, None] = {}

        for transaction in payload.transactions:
            normalized_timestamp = self._normalize_timestamp(
                transaction.timestamp, transaction.tx_hash
            )
            self._validate_supported_timestamp(normalized_timestamp, transaction.tx_hash)
            pricing_date = normalized_timestamp.date()
            self._validate_supported_date(pricing_date)
            normalized_transactions.append((transaction, pricing_date))
            unique_dates.setdefault(pricing_date, None)

        rates_by_date: dict[date, float] = {}
        for pricing_date in unique_dates:
            rates_by_date[pricing_date] = await self._client.fetch_eth_usd_rate(pricing_date)

        items = []
        for transaction, pricing_date in normalized_transactions:
            enriched_transaction = transaction.model_dump()
            enriched_transaction["pricing"] = PricingPayload(
                pricing_date_utc=pricing_date,
                eth_usd=rates_by_date[pricing_date],
            )
            items.append(enriched_transaction)

        return EnrichTransactionsResponse(items=items)

    def _validate_supported_timestamp(
        self, normalized_timestamp: datetime, tx_hash: str
    ) -> None:
        current_timestamp = self._now_provider().astimezone(UTC)
        if normalized_timestamp > current_timestamp:
            raise InvalidTransactionPayload(
                f"Transaction {tx_hash} has a future timestamp."
            )

    def _validate_supported_date(self, pricing_date: date) -> None:
        current_date = self._now_provider().astimezone(UTC).date()
        if self._settings.coingecko_api_tier != "pro":
            earliest_supported_date = current_date - timedelta(days=365)
            if pricing_date < earliest_supported_date:
                raise InvalidTransactionPayload(
                    "CoinGecko public/demo historical data is limited to the last 365 days."
                )

    def _normalize_timestamp(self, value: Any, tx_hash: str) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)

        if isinstance(value, bool):
            raise InvalidTransactionPayload(
                f"Transaction {tx_hash} has an unsupported timestamp format."
            )

        if isinstance(value, int):
            return self._parse_unix_timestamp(value, tx_hash)

        if isinstance(value, float):
            if value.is_integer():
                return self._parse_unix_timestamp(int(value), tx_hash)
            raise InvalidTransactionPayload(
                f"Transaction {tx_hash} has an unsupported timestamp format."
            )

        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                raise InvalidTransactionPayload(
                    f"Transaction {tx_hash} has an empty timestamp."
                )

            if normalized.isdigit():
                return self._parse_unix_timestamp(int(normalized), tx_hash)

            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"

            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError as exc:
                raise InvalidTransactionPayload(
                    f"Transaction {tx_hash} has an unsupported timestamp format."
                ) from exc

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)

            return parsed.astimezone(UTC)

        raise InvalidTransactionPayload(
            f"Transaction {tx_hash} has an unsupported timestamp format."
        )

    @staticmethod
    def _parse_unix_timestamp(value: int, tx_hash: str) -> datetime:
        if value < 0:
            raise InvalidTransactionPayload(
                f"Transaction {tx_hash} has an unsupported timestamp format."
            )

        timestamp = value / 1000 if value >= 1_000_000_000_000 else value

        try:
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except (OverflowError, OSError, ValueError) as exc:
            raise InvalidTransactionPayload(
                f"Transaction {tx_hash} has an unsupported timestamp format."
            ) from exc
