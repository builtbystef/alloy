"""Route tests use the per-test in-memory store from conftest; the Redis store is
checked against the Compose Redis, like the job queue."""

import asyncio
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient as BareTestClient

from alloy_api.config import Settings
from alloy_api.ratelimit import (
    LOGIN_PER_EMAIL,
    LOGIN_PER_IP,
    Hit,
    Limit,
    Limiter,
    MemoryRateLimitStore,
    RedisRateLimitStore,
    create_rate_limit_store,
    get_limiter,
    per_ip,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient
    from tests.conftest import Actor, Outbox

TWO_PER_MINUTE = Limit("test", 2, timedelta(minutes=1))
CREDENTIALS = {"email": "ada@example.com", "password": "correct horse battery"}


# --- Stores -------------------------------------------------------------------


def test_settings_pick_the_store():
    redis = create_rate_limit_store(Settings(rate_limit_store="redis"))
    memory = create_rate_limit_store(Settings(rate_limit_store="memory"))
    assert isinstance(redis, RedisRateLimitStore)
    assert isinstance(memory, MemoryRateLimitStore)


def test_memory_store_counts_within_a_window_and_forgets_after_it():
    now = 1000.0
    store = MemoryRateLimitStore(clock=lambda: now)

    async def scenario() -> None:
        nonlocal now
        first = await store.hit("k", timedelta(seconds=30))
        assert (first.count, first.retry_after) == (1, timedelta(seconds=30))
        now += 10
        second = await store.hit("k", timedelta(seconds=30))
        assert (second.count, second.retry_after) == (2, timedelta(seconds=20))
        assert await store.peek("k") == Hit(2, timedelta(seconds=20))
        now += 20
        assert await store.peek("k") == Hit(0, timedelta(0))
        third = await store.hit("k", timedelta(seconds=30))
        assert third.count == 1
        await store.reset("k")
        assert await store.peek("k") == Hit(0, timedelta(0))

    asyncio.run(scenario())


def test_redis_store_counts_within_a_window_and_forgets_after_it():
    """Real Redis: uses a key of its own and removes it afterwards."""
    key = f"ratelimit:test:{uuid.uuid4()}"

    async def scenario() -> None:
        store = RedisRateLimitStore(str(Settings().redis_url))
        try:
            first = await store.hit(key, timedelta(seconds=30))
            second = await store.hit(key, timedelta(seconds=30))
            assert (first.count, second.count) == (1, 2)
            assert timedelta(seconds=25) < second.retry_after <= timedelta(seconds=30)
            standing = await store.peek(key)
            assert standing.count == 2
            assert timedelta(seconds=25) < standing.retry_after <= timedelta(seconds=30)
            assert await store.peek(f"{key}:missing") == Hit(0, timedelta(0))
            await store.reset(key)
            assert await store.peek(key) == Hit(0, timedelta(0))
        finally:
            await store.reset(key)
            await store.aclose()

    asyncio.run(scenario())


# --- Limiter -------------------------------------------------------------------


def test_limiter_refuses_past_the_limit_with_retry_after():
    limiter = Limiter(MemoryRateLimitStore(clock=lambda: 0.0))

    async def scenario() -> None:
        await limiter.hit(TWO_PER_MINUTE, "s")
        await limiter.hit(TWO_PER_MINUTE, "s")
        with pytest.raises(HTTPException, match="Too many attempts") as info:
            await limiter.hit(TWO_PER_MINUTE, "s")
        assert info.value.status_code == 429
        assert info.value.headers == {"Retry-After": "60"}
        await limiter.hit(TWO_PER_MINUTE, "t")

    asyncio.run(scenario())


def test_limiter_check_does_not_count_and_reset_clears():
    limiter = Limiter(MemoryRateLimitStore())

    async def scenario() -> None:
        for _ in range(5):
            await limiter.check(TWO_PER_MINUTE, "s")
        await limiter.hit(TWO_PER_MINUTE, "s")
        await limiter.hit(TWO_PER_MINUTE, "s")
        with pytest.raises(HTTPException, match="Too many attempts"):
            await limiter.check(TWO_PER_MINUTE, "s")
        await limiter.reset(TWO_PER_MINUTE, "s")
        await limiter.check(TWO_PER_MINUTE, "s")

    asyncio.run(scenario())


def test_per_ip_keys_on_the_client_address():
    """`request.client` is what Uvicorn fills from `X-Forwarded-For` in production."""
    app = FastAPI()
    store = MemoryRateLimitStore()
    app.dependency_overrides[get_limiter] = lambda: Limiter(store)

    @app.get("/", dependencies=[Depends(per_ip(TWO_PER_MINUTE))])
    async def read() -> dict[str, str]:
        return {"ok": "yes"}

    with BareTestClient(app, client=("10.0.0.1", 1234)) as client:
        assert [client.get("/").status_code for _ in range(3)] == [200, 200, 429]
        assert client.get("/").headers["retry-after"] == "60"
    with BareTestClient(app, client=("10.0.0.2", 1234)) as other:
        assert other.get("/").status_code == 200


# --- Routes --------------------------------------------------------------------


def test_login_failures_on_one_email_are_limited_and_a_success_clears_them(
    client: TestClient, rate_limits: MemoryRateLimitStore
):
    client.post("/auth/signup", json=CREDENTIALS)
    client.cookies.clear()
    wrong = {**CREDENTIALS, "password": "wrong password"}
    for _ in range(LOGIN_PER_EMAIL.limit):
        assert client.post("/auth/login", json=wrong).status_code == 401
    blocked = client.post("/auth/login", json=wrong)
    assert blocked.status_code == 429
    assert 0 < int(blocked.headers["retry-after"]) <= LOGIN_PER_EMAIL.window.total_seconds()
    # Blocked before the password is even checked.
    assert client.post("/auth/login", json=CREDENTIALS).status_code == 429
    assert client.post("/auth/login", json={**wrong, "email": "x@example.com"}).status_code == 401

    # Stands in for the window ending.
    key = Limiter.key(LOGIN_PER_EMAIL, CREDENTIALS["email"])
    asyncio.run(rate_limits.reset(key))
    assert client.post("/auth/login", json=CREDENTIALS).status_code == 200
    assert asyncio.run(rate_limits.peek(key)).count == 0


def test_login_attempts_from_one_address_are_limited(client: TestClient):
    """Distinct emails, so only the address counter moves."""
    for i in range(LOGIN_PER_IP.limit):
        attempt = {"email": f"user{i}@example.com", "password": "whatever it is"}
        assert client.post("/auth/login", json=attempt).status_code == 401
    assert client.post("/auth/login", json=CREDENTIALS).status_code == 429


def test_signups_from_one_address_are_limited(client: TestClient):
    for i in range(10):
        response = client.post(
            "/auth/signup", json={**CREDENTIALS, "email": f"user{i}@example.com"}
        )
        assert response.status_code == 201, response.text
    response = client.post("/auth/signup", json={**CREDENTIALS, "email": "last@example.com"})
    assert response.status_code == 429


def test_password_reset_emails_to_one_address_are_limited(client: TestClient, outbox: Outbox):
    """Unknown addresses count too, so the limit reveals nothing the 204 hides."""
    client.post("/auth/signup", json=CREDENTIALS)
    outbox.clear()
    for _ in range(3):
        assert forgot(client, "ADA@example.com") == 204
    assert forgot(client, CREDENTIALS["email"]) == 429
    assert len(outbox) == 3
    for _ in range(3):
        assert forgot(client, "nobody@example.com") == 204
    assert forgot(client, "nobody@example.com") == 429
    assert len(outbox) == 3


def forgot(client: TestClient, email: str) -> int:
    return client.post("/auth/forgot-password", json={"email": email}).status_code


def test_verification_resends_are_limited_per_user(client: TestClient, outbox: Outbox):
    client.post("/auth/signup", json=CREDENTIALS)
    outbox.clear()
    for _ in range(3):
        assert client.post("/auth/resend-verification").status_code == 204
    assert client.post("/auth/resend-verification").status_code == 429
    assert len(outbox) == 3


def test_token_endpoints_are_limited_per_address(client: TestClient):
    for _ in range(10):
        assert client.get("/invites/nope").status_code == 404
    assert client.get("/invites/nope").status_code == 429
    # The token endpoints share one counter: it is the address that is spraying.
    assert client.post("/auth/verify-email", json={"token": "nope"}).status_code == 429
    assert (
        client.post(
            "/auth/reset-password", json={"token": "nope", "new_password": "long enough"}
        ).status_code
        == 429
    )


def test_invite_acceptance_is_limited_per_user(alice: Actor, new_actor: Callable[[str], Actor]):
    guest = new_actor("guest@example.com")
    for _ in range(10):
        assert alice.client.post("/invites/nope/accept", headers=guest.headers).status_code == 404
    assert alice.client.post("/invites/nope/accept", headers=guest.headers).status_code == 429
    assert alice.client.post("/invites/nope/accept", headers=alice.headers).status_code == 404
