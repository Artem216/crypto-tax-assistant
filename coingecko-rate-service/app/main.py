"""Application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from app.api.routes import router
from app.clients.coingecko import CoinGeckoClient
from app.core.config import get_settings
from app.services.rate_resolver import HistoricalRateResolver


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = CoinGeckoClient(settings)
    await client.open()

    app.state.settings = settings
    app.state.coingecko_client = client
    app.state.rate_resolver = HistoricalRateResolver(client=client, settings=settings)

    try:
        yield
    finally:
        await client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CoinGecko ETH/USD Rate Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.app_port)
