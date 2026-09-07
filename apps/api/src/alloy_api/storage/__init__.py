"""Object storage behind one small interface.

`ObjectStore` (base.py) is the contract, `S3ObjectStore` (s3.py) the only
implementation so far; it covers RustFS locally and any hosted S3-compatible
service. To add a backend that speaks something else: write a class with the
same methods, add its name to `StorageProvider`, and return it from
`create_object_store`. Handlers ask for an `ObjectStoreDep` and never see
the provider.
"""

from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import Depends, Request

from alloy_api.storage.base import ObjectInfo, ObjectNotFoundError, ObjectStore
from alloy_api.storage.s3 import S3Config, S3ObjectStore

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from alloy_api.config import Settings

StorageProvider = Literal["s3"]


def create_object_store(settings: Settings) -> AbstractAsyncContextManager[ObjectStore]:
    """The configured store, to be entered for the app's lifetime."""
    match settings.storage_provider:
        case "s3":
            return S3ObjectStore(
                S3Config(
                    bucket=settings.storage_bucket,
                    access_key=settings.storage_access_key,
                    secret_key=settings.storage_secret_key.get_secret_value(),
                    region=settings.storage_region,
                    endpoint_url=url_or_none(settings.storage_endpoint_url),
                    public_endpoint_url=url_or_none(settings.storage_public_endpoint_url),
                    path_style=settings.storage_path_style,
                )
            )


def url_or_none(url: object) -> str | None:
    """`HttpUrl` adds a trailing slash, which botocore would double."""
    return None if url is None else str(url).rstrip("/")


async def get_object_store(request: Request) -> ObjectStore:
    """The store the lifespan put on `request.state`."""
    store: ObjectStore = request.state.object_store
    return store


ObjectStoreDep = Annotated[ObjectStore, Depends(get_object_store)]

__all__ = [
    "ObjectInfo",
    "ObjectNotFoundError",
    "ObjectStore",
    "ObjectStoreDep",
    "S3Config",
    "S3ObjectStore",
    "StorageProvider",
    "create_object_store",
]
