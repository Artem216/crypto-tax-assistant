import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.core.config import get_settings
from app.main import create_app


WALLET_ADDRESS = "0x1111111111111111111111111111111111111111"


def test_invalid_wallet_address_returns_422(client) -> None:
    response = client.get("/api/v1/wallets/not-an-address/native-transactions")
    assert response.status_code == 422


def test_invalid_chain_id_returns_422(client) -> None:
    response = client.get(
        f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions",
        params={"chain_id": 0},
    )
    assert response.status_code == 422


def test_invalid_page_size_returns_422(client) -> None:
    response = client.get(
        f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions",
        params={"page_size": 1001},
    )
    assert response.status_code == 422


def test_invalid_sort_returns_422(client) -> None:
    response = client.get(
        f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions",
        params={"sort": "ascending"},
    )
    assert response.status_code == 422


def test_invalid_contract_address_returns_422(client) -> None:
    response = client.get(
        f"/api/v1/wallets/{WALLET_ADDRESS}/erc20-transfers",
        params={"contract_address": "bad-address"},
    )
    assert response.status_code == 422


def test_invalid_block_range_returns_422(client) -> None:
    response = client.get(
        f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions",
        params={"start_block": 100, "end_block": 99},
    )
    assert response.status_code == 422


def test_default_chain_id_comes_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("ETHERSCAN_API_KEY", "test-api-key")
    monkeypatch.setenv("DEFAULT_CHAIN_ID", "8453")
    get_settings.cache_clear()

    with TestClient(create_app()) as test_client:
        with respx.mock(assert_all_called=True) as mock:
            route = mock.get("https://api.etherscan.io/v2/api").mock(
                return_value=Response(
                    200,
                    json={"status": "1", "message": "OK", "result": []},
                )
            )
            response = test_client.get(f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions")

    assert response.status_code == 200
    assert route.calls[0].request.url.params["chainid"] == "8453"
