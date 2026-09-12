from typing import TYPE_CHECKING

import pytest

from alloy_server.config import Settings
from alloy_server.integrations.storage import get_object_store
from alloy_server.integrations.storage.memory import MemoryObjectStore
from alloy_server.main import app

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_liveness_db_and_storage_answer(client: TestClient):
    for path in ("/health/", "/health/db", "/health/storage"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.json() == {"status": "ok"}


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
