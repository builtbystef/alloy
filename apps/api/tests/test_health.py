from alloy_api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_greeting() -> None:
    response = client.get("/api/hello/alloy")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, alloy!"}
