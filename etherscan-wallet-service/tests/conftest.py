import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def set_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ETHERSCAN_API_KEY", "test-api-key")
    monkeypatch.setenv("APP_PORT", "8000")
    monkeypatch.setenv("ETHERSCAN_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("ETHERSCAN_RPS_LIMIT", "3")
    monkeypatch.setenv("DEFAULT_CHAIN_ID", "1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client
