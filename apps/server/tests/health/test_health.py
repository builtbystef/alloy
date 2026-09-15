from typing import TYPE_CHECKING

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


class DownStore(MemoryObjectStore):
    async def ping(self) -> None:
        msg = "no bucket"
        raise RuntimeError(msg)


def test_a_dead_store_is_a_503(client: TestClient):
    app.dependency_overrides[get_object_store] = DownStore
    response = client.get("/health/storage")
    assert response.status_code == 503
    assert response.json()["detail"] == "storage is unavailable"
