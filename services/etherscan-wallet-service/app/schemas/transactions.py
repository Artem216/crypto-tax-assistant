from typing import Any

from pydantic import BaseModel

from app.schemas.common import CommonTxQueryParams, Erc20TxQueryParams, EthereumAddress, SortOrder


class NativeTransactionItem(BaseModel):
    tx_hash: str
    block_number: str
    timestamp: str
    from_address: EthereumAddress
    to_address: str | None
    value_wei: str
    gas_price_wei: str
    gas_used: str
    fee_wei: str
    status: str
    is_error: bool
    method_id: str | None
    function_name: str | None


class NativeTransactionsResponse(BaseModel):
    wallet_address: EthereumAddress
    chain_id: int
    page: int
    page_size: int
    sort: SortOrder
    items: list[NativeTransactionItem]


class Erc20TransactionItem(BaseModel):
    tx_hash: str
    block_number: str
    timestamp: str
    from_address: EthereumAddress
    to_address: str | None
    contract_address: EthereumAddress
    token_name: str
    token_symbol: str
    token_decimals: str
    value_raw: str
    gas_price_wei: str
    gas_used: str
    status: str
    method_id: str | None
    function_name: str | None


class Erc20TransactionsResponse(BaseModel):
    wallet_address: EthereumAddress
    chain_id: int
    page: int
    page_size: int
    sort: SortOrder
    items: list[Erc20TransactionItem]


def map_native_transactions(
    address: str,
    query: CommonTxQueryParams,
    rows: list[dict[str, Any]],
) -> NativeTransactionsResponse:
    items = [
        NativeTransactionItem(
            tx_hash=row["hash"],
            block_number=row["blockNumber"],
            timestamp=row["timeStamp"],
            from_address=row["from"],
            to_address=_normalize_address(row.get("to")),
            value_wei=row.get("value", "0"),
            gas_price_wei=row.get("gasPrice", "0"),
            gas_used=row.get("gasUsed", "0"),
            fee_wei=_calculate_fee_wei(row),
            status=_derive_status(row),
            is_error=row.get("isError", "0") == "1",
            method_id=_normalize_optional_string(row.get("methodId")),
            function_name=_normalize_optional_string(row.get("functionName")),
        )
        for row in rows
    ]

    return NativeTransactionsResponse(
        wallet_address=address,
        chain_id=query.chain_id,
        page=query.page,
        page_size=query.page_size,
        sort=query.sort,
        items=items,
    )


def map_erc20_transactions(
    address: str,
    query: Erc20TxQueryParams,
    rows: list[dict[str, Any]],
) -> Erc20TransactionsResponse:
    items = [
        Erc20TransactionItem(
            tx_hash=row["hash"],
            block_number=row["blockNumber"],
            timestamp=row["timeStamp"],
            from_address=row["from"],
            to_address=_normalize_address(row.get("to")),
            contract_address=row["contractAddress"],
            token_name=row.get("tokenName", ""),
            token_symbol=row.get("tokenSymbol", ""),
            token_decimals=row.get("tokenDecimal", "0"),
            value_raw=row.get("value", "0"),
            gas_price_wei=row.get("gasPrice", "0"),
            gas_used=row.get("gasUsed", "0"),
            status=_derive_status(row),
            method_id=_normalize_optional_string(row.get("methodId")),
            function_name=_normalize_optional_string(row.get("functionName")),
        )
        for row in rows
    ]

    return Erc20TransactionsResponse(
        wallet_address=address,
        chain_id=query.chain_id,
        page=query.page,
        page_size=query.page_size,
        sort=query.sort,
        items=items,
    )


def _normalize_address(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _calculate_fee_wei(row: dict[str, Any]) -> str:
    try:
        gas_price = int(str(row.get("gasPrice", "0")))
        gas_used = int(str(row.get("gasUsed", "0")))
    except ValueError:
        return "0"
    return str(gas_price * gas_used)


def _derive_status(row: dict[str, Any]) -> str:
    receipt_status = row.get("txreceipt_status")
    is_error = row.get("isError")

    if receipt_status == "1" and is_error in (None, "0"):
        return "success"
    if receipt_status == "0" or is_error == "1":
        return "failed"
    if is_error == "0":
        return "success"
    return "unknown"
