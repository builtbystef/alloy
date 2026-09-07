from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from alloy_api.config import Settings, get_settings
from alloy_api.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(app_name="Test API")
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
