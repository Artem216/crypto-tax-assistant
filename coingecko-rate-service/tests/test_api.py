from datetime import UTC, datetime
from typing import Iterator

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def _history_url(tier: str) -> str:
    if tier == "pro":
        return "https://pro-api.coingecko.com/api/v3/coins/ethereum/history"
    return "https://api.coingecko.com/api/v3/coins/ethereum/history"


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 5, 16, 12, 0, tzinfo=UTC)


@pytest.fixture
def client_factory(
    monkeypatch: pytest.MonkeyPatch, fixed_now: datetime
) -> Iterator[TestClient]:
    clients: list[TestClient] = []

    def _make_client(*, tier: str = "public", api_key: str | None = None) -> TestClient:
        monkeypatch.setenv("COINGECKO_API_TIER", tier)
        monkeypatch.setenv("COINGECKO_TIMEOUT_SECONDS", "1")
        monkeypatch.setenv("COINGECKO_RETRY_ATTEMPTS", "0")
        monkeypatch.setenv("COINGECKO_RPS_LIMIT", "10")

        if api_key is None:
            monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
        else:
            monkeypatch.setenv("COINGECKO_API_KEY", api_key)

        get_settings.cache_clear()
        client = TestClient(app)
        client.__enter__()
        client.app.state.rate_resolver._now_provider = lambda: fixed_now
        clients.append(client)
        return client

    yield _make_client

    for client in reversed(clients):
        client.__exit__(None, None, None)
    get_settings.cache_clear()


@respx.mock
def test_enrich_batch_success(client_factory) -> None:
    client = client_factory()

    respx.get(
        _history_url("public"),
        params={"date": "13-05-2026", "localization": "false"},
    ).mock(
        return_value=httpx.Response(
            200, json={"market_data": {"current_price": {"usd": 2480.11}}}
        )
    )
    respx.get(
        _history_url("public"),
        params={"date": "14-05-2026", "localization": "false"},
    ).mock(
        return_value=httpx.Response(
            200, json={"market_data": {"current_price": {"usd": 2510.42}}}
        )
    )
    respx.get(
        _history_url("public"),
        params={"date": "15-05-2026", "localization": "false"},
    ).mock(
        return_value=httpx.Response(
            200, json={"market_data": {"current_price": {"usd": 2533.77}}}
        )
    )

    response = client.post(
        "/api/v1/rates/eth-usd/enrich",
        json={
            "transactions": [
                {
                    "tx_hash": "0x01",
                    "timestamp": "2026-05-13T08:30:00Z",
                    "kind": "buy",
                },
                {
                    "tx_hash": "0x02",
                    "timestamp": "2026-05-14T12:00:00+00:00",
                    "amount_eth": "1.5",
                },
                {
                    "tx_hash": "0x03",
                    "timestamp": "2026-05-15T21:00:00+00:00",
                    "note": "manual import",
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "asset": "ETH",
        "quote_currency": "USD",
        "items": [
            {
                "tx_hash": "0x01",
                "timestamp": "2026-05-13T08:30:00Z",
                "kind": "buy",
                "pricing": {
                    "pricing_date_utc": "2026-05-13",
                    "eth_usd": 2480.11,
                    "coin_id": "ethereum",
                    "source": "coingecko",
                },
            },
            {
                "tx_hash": "0x02",
                "timestamp": "2026-05-14T12:00:00+00:00",
                "amount_eth": "1.5",
                "pricing": {
                    "pricing_date_utc": "2026-05-14",
                    "eth_usd": 2510.42,
                    "coin_id": "ethereum",
                    "source": "coingecko",
                },
            },
            {
                "tx_hash": "0x03",
                "timestamp": "2026-05-15T21:00:00+00:00",
                "note": "manual import",
                "pricing": {
                    "pricing_date_utc": "2026-05-15",
                    "eth_usd": 2533.77,
                    "coin_id": "ethereum",
                    "source": "coingecko",
                },
            },
        ],
    }


@respx.mock
def test_same_utc_day_is_deduplicated(client_factory) -> None:
    client = client_factory()
    route = respx.get(
        _history_url("public"),
        params={"date": "15-05-2026", "localization": "false"},
    ).mock(
        return_value=httpx.Response(
            200, json={"market_data": {"current_price": {"usd": 2600.0}}}
        )
    )

    response = client.post(
        "/api/v1/rates/eth-usd/enrich",
        json={
            "transactions": [
                {"tx_hash": "0xaa", "timestamp": "2026-05-15T00:00:00Z"},
                {"tx_hash": "0xbb", "timestamp": "2026-05-15T23:59:59+00:00"},
            ]
        },
    )

    assert response.status_code == 200
    assert route.call_count == 1
    body = response.json()
    assert body["items"][0]["pricing"]["eth_usd"] == 2600.0
    assert body["items"][1]["pricing"]["eth_usd"] == 2600.0


@respx.mock
def test_timestamp_formats_parse_to_same_utc_day(client_factory) -> None:
    client = client_factory()
    unix_seconds = int(datetime(2026, 5, 15, 0, 0, tzinfo=UTC).timestamp())
    route = respx.get(
        _history_url("public"),
        params={"date": "15-05-2026", "localization": "false"},
    ).mock(
        return_value=httpx.Response(
            200, json={"market_data": {"current_price": {"usd": 2555.5}}}
        )
    )

    response = client.post(
        "/api/v1/rates/eth-usd/enrich",
        json={
            "transactions": [
                {"tx_hash": "0x1", "timestamp": "2026-05-15T00:00:00Z"},
                {"tx_hash": "0x2", "timestamp": unix_seconds},
                {"tx_hash": "0x3", "timestamp": str(unix_seconds)},
            ]
        },
    )

    assert response.status_code == 200
    assert route.call_count == 1
    assert [item["pricing"]["pricing_date_utc"] for item in response.json()["items"]] == [
        "2026-05-15",
        "2026-05-15",
        "2026-05-15",
    ]


@respx.mock
def test_timezone_offset_normalizes_to_utc_date(client_factory) -> None:
    client = client_factory()
    respx.get(
        _history_url("public"),
        params={"date": "15-05-2026", "localization": "false"},
    ).mock(
        return_value=httpx.Response(
            200, json={"market_data": {"current_price": {"usd": 2499.0}}}
        )
    )

    response = client.post(
        "/api/v1/rates/eth-usd/enrich",
        json={"transactions": [{"tx_hash": "0xabc", "timestamp": "2026-05-16T01:15:00+03:00"}]},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["pricing"]["pricing_date_utc"] == "2026-05-15"


def test_public_tier_rejects_transactions_older_than_365_days(client_factory) -> None:
    client = client_factory()

    response = client.post(
        "/api/v1/rates/eth-usd/enrich",
        json={"transactions": [{"tx_hash": "0xold", "timestamp": "2025-05-15T00:00:00Z"}]},
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "CoinGecko public/demo historical data is limited to the last 365 days."
    )


def test_future_timestamp_is_rejected(client_factory) -> None:
    client = client_factory()

    response = client.post(
        "/api/v1/rates/eth-usd/enrich",
        json={"transactions": [{"tx_hash": "0xfuture", "timestamp": "2026-05-16T12:00:01Z"}]},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Transaction 0xfuture has a future timestamp."


@respx.mock
def test_pro_tier_accepts_older_transactions(client_factory) -> None:
    client = client_factory(tier="pro", api_key="secret")
    respx.get(
        _history_url("pro"),
        params={"date": "15-05-2025", "localization": "false"},
    ).mock(
        return_value=httpx.Response(
            200, json={"market_data": {"current_price": {"usd": 3200.0}}}
        )
    )

    response = client.post(
        "/api/v1/rates/eth-usd/enrich",
        json={"transactions": [{"tx_hash": "0xold", "timestamp": "2025-05-15T00:00:00Z"}]},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["pricing"]["pricing_date_utc"] == "2025-05-15"


@pytest.mark.parametrize(
    ("response_or_exc", "expected_status", "expected_detail"),
    [
        (
            httpx.Response(429, json={"error": "rate limit"}),
            503,
            "CoinGecko rate limit exceeded.",
        ),
        (
            httpx.Response(500, json={"error": "server"}),
            503,
            "CoinGecko returned HTTP 500.",
        ),
        (
            httpx.Response(200, text="not-json"),
            502,
            "CoinGecko returned an invalid JSON response.",
        ),
        (
            httpx.Response(200, json={"market_data": {"current_price": {}}}),
            502,
            "CoinGecko response does not contain market_data.current_price.usd.",
        ),
        (
            httpx.TimeoutException("boom"),
            503,
            "CoinGecko request timed out.",
        ),
    ],
)
@respx.mock
def test_upstream_failures_are_mapped_to_expected_status_codes(
    client_factory, response_or_exc, expected_status: int, expected_detail: str
) -> None:
    client = client_factory()
    route = respx.get(
        _history_url("public"),
        params={"date": "15-05-2026", "localization": "false"},
    )
    route.mock(side_effect=response_or_exc if isinstance(response_or_exc, Exception) else None)
    if not isinstance(response_or_exc, Exception):
        route.mock(return_value=response_or_exc)

    response = client.post(
        "/api/v1/rates/eth-usd/enrich",
        json={"transactions": [{"tx_hash": "0xfail", "timestamp": "2026-05-15T00:00:00Z"}]},
    )

    assert response.status_code == expected_status
    assert response.json()["detail"] == expected_detail


def test_health_endpoint(client_factory) -> None:
    client = client_factory()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
