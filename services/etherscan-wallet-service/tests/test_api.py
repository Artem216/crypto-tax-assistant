import httpx
import respx
from httpx import Response


WALLET_ADDRESS = "0x1111111111111111111111111111111111111111"
TOKEN_ADDRESS = "0x2222222222222222222222222222222222222222"


def test_native_transactions_endpoint_success(client) -> None:
    payload = {
        "status": "1",
        "message": "OK",
        "result": [
            {
                "hash": "0xabc",
                "blockNumber": "123",
                "timeStamp": "1710000000",
                "from": WALLET_ADDRESS,
                "to": TOKEN_ADDRESS,
                "value": "1000000000000000000",
                "gasPrice": "20000000000",
                "gasUsed": "21000",
                "isError": "0",
                "txreceipt_status": "1",
                "methodId": "0xa9059cbb",
                "functionName": "transfer(address,uint256)",
            }
        ],
    }

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://api.etherscan.io/v2/api").mock(return_value=Response(200, json=payload))
        response = client.get(
            f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions",
            params={"page": 2, "page_size": 1, "sort": "asc"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["wallet_address"] == WALLET_ADDRESS
    assert body["page"] == 2
    assert body["page_size"] == 1
    assert body["sort"] == "asc"
    assert body["items"][0]["fee_wei"] == "420000000000000"
    assert body["items"][0]["status"] == "success"
    assert body["items"][0]["is_error"] is False


def test_erc20_transfers_endpoint_success(client) -> None:
    payload = {
        "status": "1",
        "message": "OK",
        "result": [
            {
                "hash": "0xdef",
                "blockNumber": "456",
                "timeStamp": "1710001000",
                "from": WALLET_ADDRESS,
                "to": TOKEN_ADDRESS,
                "contractAddress": TOKEN_ADDRESS,
                "tokenName": "USD Coin",
                "tokenSymbol": "USDC",
                "tokenDecimal": "6",
                "value": "2500000",
                "gasPrice": "5000000000",
                "gasUsed": "65000",
                "methodId": "0xa9059cbb",
                "functionName": "transfer(address,uint256)",
            }
        ],
    }

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://api.etherscan.io/v2/api").mock(return_value=Response(200, json=payload))
        response = client.get(
            f"/api/v1/wallets/{WALLET_ADDRESS}/erc20-transfers",
            params={"contract_address": TOKEN_ADDRESS},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["wallet_address"] == WALLET_ADDRESS
    assert body["items"][0]["contract_address"] == TOKEN_ADDRESS
    assert body["items"][0]["token_symbol"] == "USDC"
    assert body["items"][0]["value_raw"] == "2500000"
    assert body["items"][0]["status"] == "unknown"


def test_no_transactions_found_returns_empty_items(client) -> None:
    payload = {
        "status": "0",
        "message": "No transactions found",
        "result": "No transactions found",
    }

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://api.etherscan.io/v2/api").mock(return_value=Response(200, json=payload))
        response = client.get(f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_upstream_timeout_returns_502(client) -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://api.etherscan.io/v2/api").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        response = client.get(f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions")

    assert response.status_code == 502
    assert response.json()["detail"] == "Etherscan request timed out."


def test_upstream_rate_limit_returns_503(client) -> None:
    payload = {
        "status": "0",
        "message": "NOTOK",
        "result": "Max rate limit reached, please use API Key for higher rate limit",
    }

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://api.etherscan.io/v2/api").mock(return_value=Response(200, json=payload))
        response = client.get(f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions")

    assert response.status_code == 503
    assert response.json()["detail"] == "Etherscan rate limit exceeded."


def test_unsupported_chain_returns_400(client) -> None:
    payload = {
        "status": "0",
        "message": "NOTOK",
        "result": "Missing or unsupported chainid parameter (required for v2 api), please see chainlist for the list of supported chainids",
    }

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://api.etherscan.io/v2/api").mock(return_value=Response(200, json=payload))
        response = client.get(
            f"/api/v1/wallets/{WALLET_ADDRESS}/native-transactions",
            params={"chain_id": 999999},
        )

    assert response.status_code == 400
    assert "unsupported chainid" in response.json()["detail"].lower()
