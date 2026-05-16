from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.clients.etherscan import EtherscanClient
from app.core.config import get_settings
from app.core.errors import UpstreamBadRequest, UpstreamRateLimited, UpstreamServiceUnavailable


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = EtherscanClient(settings)
    await client.open()
    app.state.settings = settings
    app.state.etherscan_client = client
    yield
    await client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Etherscan Wallet Service",
        version="0.1.0",
        docs_url="/docs",
        lifespan=lifespan,
    )
    app.include_router(router)

    @app.exception_handler(UpstreamBadRequest)
    async def handle_upstream_bad_request(
        request: Request,
        exc: UpstreamBadRequest,
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.message})

    @app.exception_handler(UpstreamRateLimited)
    async def handle_upstream_rate_limit(
        request: Request,
        exc: UpstreamRateLimited,
    ) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": exc.message})

    @app.exception_handler(UpstreamServiceUnavailable)
    async def handle_upstream_unavailable(
        request: Request,
        exc: UpstreamServiceUnavailable,
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": exc.message})

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)


if __name__ == "__main__":
    run()
