"""CoinGecko API client."""

import asyncio
from collections import deque
from datetime import date
from time import monotonic
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import (
    UpstreamBadResponse,
    UpstreamRateLimited,
    UpstreamServiceUnavailable,
)


class AsyncRateLimiter:
    """A lightweight async rate limiter based on calls-per-second."""

    def __init__(self, rate_limit: int) -> None:
        self._rate_limit = rate_limit
        self._lock = asyncio.Lock()
        self._timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = monotonic()
                while self._timestamps and now - self._timestamps[0] >= 1:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._rate_limit:
                    self._timestamps.append(now)
                    return

                sleep_for = max(0.0, 1 - (now - self._timestamps[0]))
                await asyncio.sleep(sleep_for)


class CoinGeckoClient:
    """HTTP client for CoinGecko historical ETH/USD prices."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._rate_limiter = AsyncRateLimiter(settings.coingecko_rps_limit)
        self._http_client: httpx.AsyncClient | None = None

    async def open(self) -> None:
        headers = {"accept": "application/json"}
        if self._settings.coingecko_api_header_name and self._settings.coingecko_api_key:
            headers[self._settings.coingecko_api_header_name] = self._settings.coingecko_api_key

        self._http_client = httpx.AsyncClient(
            base_url=self._settings.coingecko_base_url,
            headers=headers,
            timeout=httpx.Timeout(self._settings.coingecko_timeout_seconds),
        )

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def fetch_eth_usd_rate(self, pricing_date: date) -> float:
        payload = await self._request(
            "/coins/ethereum/history",
            params={
                "date": pricing_date.strftime("%d-%m-%Y"),
                "localization": "false",
            },
        )

        try:
            usd_price = payload["market_data"]["current_price"]["usd"]
        except (KeyError, TypeError) as exc:
            raise UpstreamBadResponse(
                "CoinGecko response does not contain market_data.current_price.usd."
            ) from exc

        if not isinstance(usd_price, (int, float)) or isinstance(usd_price, bool):
            raise UpstreamBadResponse("CoinGecko returned an invalid USD price.")

        return float(usd_price)

    async def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._http_client is None:
            raise RuntimeError("CoinGecko client has not been opened.")

        attempts = self._settings.coingecko_retry_attempts + 1

        for attempt_index in range(attempts):
            try:
                await self._rate_limiter.acquire()
                response = await self._http_client.get(path, params=params)
            except httpx.TimeoutException as exc:
                if attempt_index < attempts - 1:
                    await asyncio.sleep(self._backoff_seconds(attempt_index))
                    continue
                raise UpstreamServiceUnavailable("CoinGecko request timed out.") from exc
            except httpx.HTTPError as exc:
                if attempt_index < attempts - 1:
                    await asyncio.sleep(self._backoff_seconds(attempt_index))
                    continue
                raise UpstreamServiceUnavailable("Failed to reach CoinGecko.") from exc

            if response.status_code == 429:
                if attempt_index < attempts - 1:
                    await asyncio.sleep(self._backoff_seconds(attempt_index))
                    continue
                raise UpstreamRateLimited("CoinGecko rate limit exceeded.")

            if response.status_code >= 500:
                if attempt_index < attempts - 1:
                    await asyncio.sleep(self._backoff_seconds(attempt_index))
                    continue
                raise UpstreamServiceUnavailable(
                    f"CoinGecko returned HTTP {response.status_code}."
                )

            if response.status_code >= 400:
                raise UpstreamBadResponse(
                    f"CoinGecko rejected the request with HTTP {response.status_code}."
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise UpstreamBadResponse(
                    "CoinGecko returned an invalid JSON response."
                ) from exc

            if not isinstance(payload, dict):
                raise UpstreamBadResponse(
                    "CoinGecko returned an unexpected response format."
                )

            return payload

        raise UpstreamServiceUnavailable("CoinGecko request failed after retries.")

    @staticmethod
    def _backoff_seconds(attempt_index: int) -> float:
        return min(1.0, 0.25 * (attempt_index + 1))
