from app.schemas.common import CommonTxQueryParams, Erc20TxQueryParams
from app.schemas.transactions import map_erc20_transactions, map_native_transactions


WALLET_ADDRESS = "0x1111111111111111111111111111111111111111"
OTHER_ADDRESS = "0x2222222222222222222222222222222222222222"


def test_map_native_transactions_calculates_fee_and_status() -> None:
    query = CommonTxQueryParams(chain_id=1, page=1, page_size=100, sort="desc")
    rows = [
        {
            "hash": "0xabc",
            "blockNumber": "123",
            "timeStamp": "1710000000",
            "from": WALLET_ADDRESS,
            "to": OTHER_ADDRESS,
            "value": "42",
            "gasPrice": "2",
            "gasUsed": "21000",
            "isError": "0",
            "txreceipt_status": "1",
            "methodId": "0x",
            "functionName": "",
        }
    ]

    response = map_native_transactions(address=WALLET_ADDRESS, query=query, rows=rows)

    assert response.chain_id == 1
    assert response.items[0].fee_wei == "42000"
    assert response.items[0].status == "success"
    assert response.items[0].method_id == "0x"
    assert response.items[0].function_name is None


def test_map_erc20_transactions_preserves_raw_values() -> None:
    query = Erc20TxQueryParams(chain_id=1, page=1, page_size=100, sort="desc")
    rows = [
        {
            "hash": "0xdef",
            "blockNumber": "456",
            "timeStamp": "1710001000",
            "from": WALLET_ADDRESS,
            "to": OTHER_ADDRESS,
            "contractAddress": OTHER_ADDRESS,
            "tokenName": "USD Coin",
            "tokenSymbol": "USDC",
            "tokenDecimal": "6",
            "value": "2500000",
            "gasPrice": "10",
            "gasUsed": "50000",
            "methodId": "",
            "functionName": "",
        }
    ]

    response = map_erc20_transactions(address=WALLET_ADDRESS, query=query, rows=rows)

    assert response.items[0].token_decimals == "6"
    assert response.items[0].value_raw == "2500000"
    assert response.items[0].status == "unknown"
    assert response.items[0].method_id is None
    assert response.items[0].function_name is None
