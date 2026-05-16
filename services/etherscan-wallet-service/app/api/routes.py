from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.clients.etherscan import EtherscanClient
from app.schemas.common import CommonTxQueryParams, Erc20TxQueryParams, EthereumAddress, HealthResponse
from app.schemas.transactions import Erc20TransactionsResponse, NativeTransactionsResponse

router = APIRouter()


def get_etherscan_client(request: Request) -> EtherscanClient:
    return request.app.state.etherscan_client


def get_common_tx_query_params(
    request: Request,
    chain_id: Annotated[int | None, Query(gt=0)] = None,
    start_block: Annotated[int, Query(ge=0)] = 0,
    end_block: Annotated[int, Query(ge=0)] = 999_999_999,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000)] = 100,
    sort: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> CommonTxQueryParams:
    if end_block < start_block:
        raise HTTPException(status_code=422, detail="end_block must be greater than or equal to start_block")

    default_chain_id = request.app.state.settings.default_chain_id
    return CommonTxQueryParams(
        chain_id=chain_id or default_chain_id,
        start_block=start_block,
        end_block=end_block,
        page=page,
        page_size=page_size,
        sort=sort,
    )


def get_erc20_tx_query_params(
    request: Request,
    chain_id: Annotated[int | None, Query(gt=0)] = None,
    start_block: Annotated[int, Query(ge=0)] = 0,
    end_block: Annotated[int, Query(ge=0)] = 999_999_999,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000)] = 100,
    sort: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    contract_address: Annotated[str | None, Query(pattern="^0x[a-fA-F0-9]{40}$")] = None,
) -> Erc20TxQueryParams:
    if end_block < start_block:
        raise HTTPException(status_code=422, detail="end_block must be greater than or equal to start_block")

    default_chain_id = request.app.state.settings.default_chain_id
    return Erc20TxQueryParams(
        chain_id=chain_id or default_chain_id,
        start_block=start_block,
        end_block=end_block,
        page=page,
        page_size=page_size,
        sort=sort,
        contract_address=contract_address,
    )


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/api/v1/wallets/{address}/native-transactions",
    response_model=NativeTransactionsResponse,
    tags=["wallets"],
)
async def get_native_transactions(
    address: EthereumAddress,
    query: Annotated[CommonTxQueryParams, Depends(get_common_tx_query_params)],
    client: Annotated[EtherscanClient, Depends(get_etherscan_client)],
) -> NativeTransactionsResponse:
    return await client.fetch_native_transactions(address=address, query=query)


@router.get(
    "/api/v1/wallets/{address}/erc20-transfers",
    response_model=Erc20TransactionsResponse,
    tags=["wallets"],
)
async def get_erc20_transfers(
    address: EthereumAddress,
    query: Annotated[Erc20TxQueryParams, Depends(get_erc20_tx_query_params)],
    client: Annotated[EtherscanClient, Depends(get_etherscan_client)],
) -> Erc20TransactionsResponse:
    return await client.fetch_erc20_transfers(address=address, query=query)
