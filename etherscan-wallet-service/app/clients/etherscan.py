import asyncio
from collections import deque
from time import monotonic
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import UpstreamBadRequest, UpstreamRateLimited, UpstreamServiceUnavailable
from app.schemas.common import CommonTxQueryParams, Erc20TxQueryParams
from app.schemas.transactions import Erc20TransactionsResponse, NativeTransactionsResponse
from app.schemas.transactions import map_erc20_transactions, map_native_transactions


class AsyncRateLimiter:
    def __init__(self, rate_limit: int) -> None:
        self._rate_limit = max(1, rate_limit)
        self._lock = asyncio.Lock()
        self._timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = monotonic()
                while self._timestamps and now - self._timestamps[0] >= 1:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._rate_limit:
                    self._timestamps.append(now)
                    return

                wait_seconds = max(0.0, 1 - (now - self._timestamps[0]))

            await asyncio.sleep(wait_seconds)


class EtherscanClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._rate_limiter = AsyncRateLimiter(settings.etherscan_rps_limit)
        self._http_client: httpx.AsyncClient | None = None

    async def open(self) -> None:
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._settings.etherscan_timeout_seconds),
        )

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def fetch_native_transactions(
        self,
        address: str,
        query: CommonTxQueryParams,
    ) -> NativeTransactionsResponse:
        rows = await self._request(
            {
                "chainid": query.chain_id,
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": query.start_block,
                "endblock": query.end_block,
                "page": query.page,
                "offset": query.page_size,
                "sort": query.sort,
                "apikey": self._settings.etherscan_api_key,
            }
        )
        return map_native_transactions(address=address, query=query, rows=rows)

    async def fetch_erc20_transfers(
        self,
        address: str,
        query: Erc20TxQueryParams,
    ) -> Erc20TransactionsResponse:
        params: dict[str, Any] = {
            "chainid": query.chain_id,
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": query.start_block,
            "endblock": query.end_block,
            "page": query.page,
            "offset": query.page_size,
            "sort": query.sort,
            "apikey": self._settings.etherscan_api_key,
        }
        if query.contract_address is not None:
            params["contractaddress"] = query.contract_address

        rows = await self._request(params)
        return map_erc20_transactions(address=address, query=query, rows=rows)

    async def _request(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        if self._http_client is None:
            raise RuntimeError("Etherscan client has not been opened.")

        attempts = self._settings.etherscan_retry_attempts
        for attempt in range(1, attempts + 1):
            await self._rate_limiter.acquire()

            try:
                response = await self._http_client.get(
                    self._settings.etherscan_base_url,
                    params=params,
                )
            except httpx.TimeoutException as exc:
                if attempt < attempts:
                    continue
                raise UpstreamServiceUnavailable("Etherscan request timed out.") from exc
            except httpx.RequestError as exc:
                raise UpstreamServiceUnavailable("Failed to reach Etherscan.") from exc

            if response.status_code >= 500:
                if attempt < attempts:
                    continue
                raise UpstreamServiceUnavailable(
                    f"Etherscan returned HTTP {response.status_code}."
                )

            if response.status_code == 429:
                raise UpstreamRateLimited("Etherscan rate limit exceeded.")

            if response.status_code >= 400:
                raise UpstreamBadRequest(
                    f"Etherscan rejected the request with HTTP {response.status_code}."
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise UpstreamServiceUnavailable(
                    "Etherscan returned an invalid JSON response."
                ) from exc

            return self._parse_payload(payload)

        raise UpstreamServiceUnavailable("Etherscan request failed after retries.")

    def _parse_payload(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        status = str(payload.get("status", ""))
        message = str(payload.get("message", ""))
        result = payload.get("result")
        combined_message = " ".join(
            part for part in [message, result if isinstance(result, str) else ""] if part
        ).lower()

        if status == "1":
            if isinstance(result, list):
                return result
            raise UpstreamServiceUnavailable("Etherscan returned an unexpected response format.")

        if isinstance(result, list) and not result:
            return []

        if "no transactions found" in combined_message:
            return []

        if "rate limit" in combined_message or "max calls per sec" in combined_message:
            raise UpstreamRateLimited("Etherscan rate limit exceeded.")

        if "api key" in combined_message:
            raise UpstreamServiceUnavailable("Invalid or missing Etherscan API key.")

        if any(
            keyword in combined_message
            for keyword in (
                "unsupported chain",
                "unsupported chainid",
                "invalid address",
                "missing address",
                "invalid contract address",
                "invalid block",
                "invalid page",
                "invalid offset",
            )
        ):
            reason = result if isinstance(result, str) and result else message
            raise UpstreamBadRequest(reason or "Etherscan rejected the request.")

        reason = result if isinstance(result, str) and result else message
        raise UpstreamServiceUnavailable(reason or "Etherscan request failed.")
