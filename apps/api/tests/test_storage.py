"""The `ObjectStore` contract, run against every implementation: the in-memory test
double, so the route tests stay honest, and `S3ObjectStore` against the RustFS
from compose.yaml (`vp run db:up`), which is what production-shaped storage
looks like. The presigned URL tests need a real HTTP server, so they are S3-only.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import TYPE_CHECKING

import httpx2 as httpx
import pytest
from botocore.exceptions import EndpointConnectionError

from alloy_api.config import Settings
from alloy_api.storage import ObjectNotFoundError, S3ObjectStore, create_object_store
from alloy_api.storage.memory import MemoryObjectStore
from alloy_api.storage.s3 import content_disposition

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from alloy_api.storage import ObjectStore

pytestmark = pytest.mark.anyio

TTL = timedelta(minutes=5)


@asynccontextmanager
async def open_s3() -> AsyncIterator[S3ObjectStore]:
    store = create_object_store(Settings(app_name="Test API"))
    assert isinstance(store, S3ObjectStore)
    async with store:
        try:
            await store.head("contract-test/probe")
        except EndpointConnectionError as exc:
            pytest.fail(f"Object storage is not reachable. Run `vp run db:up`. ({exc})")
        yield store


@pytest.fixture
async def s3() -> AsyncIterator[S3ObjectStore]:
    async with open_s3() as store:
        yield store


@pytest.fixture(params=["memory", "s3"])
async def store(request: pytest.FixtureRequest) -> AsyncIterator[ObjectStore]:
    if request.param == "memory":
        yield MemoryObjectStore()
    else:
        async with open_s3() as s3:
            yield s3


@pytest.fixture
def prefix() -> str:
    """A fresh key space per test, so runs never see each other's objects."""
    return f"contract-test/{uuid.uuid7()}/"


async def test_put_head_get_delete(store: ObjectStore, prefix: str):
    key = prefix + "hello.txt"
    assert await store.head(key) is None
    await store.put(key, b"hello world", "text/plain")

    info = await store.head(key)
    assert info is not None
    assert (info.key, info.size, info.content_type) == (key, 11, "text/plain")
    assert await store.get(key) == b"hello world"

    await store.delete(key)
    assert await store.head(key) is None
    with pytest.raises(ObjectNotFoundError):
        await store.get(key)
    # Deleting again is not an error.
    await store.delete(key)


async def test_delete_prefix_leaves_neighbours(store: ObjectStore, prefix: str):
    await store.put(prefix + "a/1", b"1", "text/plain")
    await store.put(prefix + "a/2", b"2", "text/plain")
    await store.put(prefix + "b/1", b"3", "text/plain")
    try:
        await store.delete_prefix(prefix + "a/")
        assert await store.head(prefix + "a/1") is None
        assert await store.head(prefix + "a/2") is None
        assert await store.head(prefix + "b/1") is not None
    finally:
        await store.delete_prefix(prefix)


async def test_upload_url_accepts_one_put_of_the_declared_type_and_size(
    s3: S3ObjectStore, prefix: str
):
    key = prefix + "upload.txt"
    url = await s3.upload_url(key, "text/plain", 5, TTL)
    text = {"Content-Type": "text/plain"}
    try:
        async with httpx.AsyncClient() as http:
            wrong_type = await http.put(
                url, content=b"hello", headers={"Content-Type": "image/png"}
            )
            assert wrong_type.status_code == 403
            too_big = await http.put(url, content=b"hello!", headers=text)
            assert too_big.status_code == 403
            too_small = await http.put(url, content=b"hell", headers=text)
            assert too_small.status_code == 403
            assert await s3.head(key) is None
            ok = await http.put(url, content=b"hello", headers=text)
            assert ok.status_code == 200, ok.text
        info = await s3.head(key)
        assert info is not None
        assert (info.size, info.content_type) == (5, "text/plain")
    finally:
        await s3.delete(key)


async def test_download_url_serves_the_file_as_a_named_download(s3: S3ObjectStore, prefix: str):
    key = prefix + "download"
    await s3.put(key, b"hello world", "text/plain")
    try:
        url = await s3.download_url(key, "Årsrapport 2026.txt", TTL)
        async with httpx.AsyncClient() as http:
            response = await http.get(url)
        assert response.status_code == 200
        assert response.content == b"hello world"
        assert response.headers["content-type"] == "text/plain"
        assert response.headers["content-disposition"] == content_disposition("Årsrapport 2026.txt")
    finally:
        await s3.delete(key)


def test_content_disposition_has_an_ascii_fallback_and_a_utf8_form():
    assert content_disposition("plain.pdf") == (
        "attachment; filename=\"plain.pdf\"; filename*=UTF-8''plain.pdf"
    )
    assert content_disposition('Q3 "final".pdf') == (
        "attachment; filename=\"Q3 'final'.pdf\"; filename*=UTF-8''Q3%20%22final%22.pdf"
    )
    assert content_disposition("Årsrapport.txt") == (
        "attachment; filename=\"?rsrapport.txt\"; filename*=UTF-8''%C3%85rsrapport.txt"
    )


def test_s3_is_the_default_provider():
    store = create_object_store(Settings(app_name="Test API"))
    assert isinstance(store, S3ObjectStore)
    assert store.bucket == "alloy"
