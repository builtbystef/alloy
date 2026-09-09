"""The readiness probes: ok when the dependency answers, 503 when it does not."""

from typing import TYPE_CHECKING

import pytest

from alloy_api.config import Settings
from alloy_api.main import app
from alloy_api.storage import get_object_store
from alloy_api.storage.memory import MemoryObjectStore

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_db_and_storage_answer(client: TestClient):
    assert client.get("/health/db").json() == {"status": "ok"}
    assert client.get("/health/storage").json() == {"status": "ok"}


def test_redis_is_skipped_on_the_memory_broker(client: TestClient):
    assert client.get("/health/redis").json() == {"status": "ok"}


class DownStore(MemoryObjectStore):
    async def ping(self) -> None:
        msg = "no bucket"
        raise RuntimeError(msg)


def test_a_dead_store_is_a_503(client: TestClient):
    app.dependency_overrides[get_object_store] = DownStore
    response = client.get("/health/storage")
    assert response.status_code == 503
    assert response.json()["detail"] == "storage is unavailable"


class TestWhenRedisIsDown:
    @pytest.fixture
    def settings(self) -> Settings:
        return Settings(app_name="Test API", jobs_broker="redis", redis_url="redis://127.0.0.1:1/0")

    def test_a_dead_redis_is_a_503(self, client: TestClient):
        response = client.get("/health/redis")
        assert response.status_code == 503
        assert response.json()["detail"] == "redis is unavailable"
