"""HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.errors import (
    InvalidTransactionPayload,
    UpstreamBadResponse,
    UpstreamRateLimited,
    UpstreamServiceUnavailable,
)
from app.schemas.common import HealthResponse
from app.schemas.rates import EnrichTransactionsRequest, EnrichTransactionsResponse
from app.services.rate_resolver import HistoricalRateResolver

router = APIRouter()


def get_rate_resolver(request: Request) -> HistoricalRateResolver:
    return request.app.state.rate_resolver


@router.get("/health", tags=["health"], response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()


@router.post(
    "/api/v1/rates/eth-usd/enrich",
    tags=["rates"],
    response_model=EnrichTransactionsResponse,
)
async def enrich_eth_usd_rates(
    payload: EnrichTransactionsRequest,
    resolver: Annotated[HistoricalRateResolver, Depends(get_rate_resolver)],
) -> EnrichTransactionsResponse:
    try:
        return await resolver.enrich_transactions(payload)
    except InvalidTransactionPayload as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UpstreamBadResponse as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (UpstreamRateLimited, UpstreamServiceUnavailable) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
