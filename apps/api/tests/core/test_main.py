from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"app": "Test API"}


def test_read_health(client: TestClient):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_operation_ids(client: TestClient):
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/"]["get"]["operationId"] == "read_root"
    assert schema["paths"]["/health/"]["get"]["operationId"] == "health-read_health"
    assert schema["paths"]["/health/db"]["get"]["operationId"] == "health-read_health_db"
