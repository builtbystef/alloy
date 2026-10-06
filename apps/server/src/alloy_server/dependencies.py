"""FastAPI dependencies that read the resources the lifespan put on `request.state`."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from alloy_server.config import Settings
from alloy_server.integrations.rate_limit import Limit, RateLimiter
from alloy_server.integrations.storage import ObjectStore
from alloy_server.resources import Resources


def get_resources(request: Request) -> Resources:
    resources: Resources = request.state.resources
    return resources


ResourcesDep = Annotated[Resources, Depends(get_resources)]


def get_settings(resources: ResourcesDep) -> Settings:
    return resources.settings


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_session(resources: ResourcesDep) -> AsyncIterator[AsyncSession]:
    """One session per request; handlers commit explicitly."""
    async with resources.session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_object_store(resources: ResourcesDep) -> ObjectStore:
    return resources.object_store


ObjectStoreDep = Annotated[ObjectStore, Depends(get_object_store)]


def get_rate_limiter(resources: ResourcesDep) -> RateLimiter:
    return RateLimiter(resources.rate_limit_store)


RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


def client_ip(request: Request) -> str:
    """No socket (a bare ASGI scope in tests) shares one "unknown" counter rather
    than escaping the limit."""
    return request.client.host if request.client else "unknown"


ClientIp = Annotated[str, Depends(client_ip)]


def per_ip(limit: Limit) -> Callable[[Request, RateLimiter], Awaitable[None]]:
    async def dependency(request: Request, limiter: RateLimiterDep) -> None:
        await limiter.hit(limit, client_ip(request))

    return dependency
