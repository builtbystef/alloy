from dataclasses import dataclass
from typing import TYPE_CHECKING

from alloy_server.db.base import utcnow
from alloy_server.shared.exceptions import ConflictError, PayloadTooLargeError

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from alloy_server.integrations.storage.base import ObjectInfo, ObjectStore


@dataclass(frozen=True, slots=True)
class UploadStorage:
    """The object store plus what one kind of upload needs from the settings: its
    size limit and how long the URLs it hands out live. Each module builds one
    with its own limit as a dependency."""

    store: ObjectStore
    max_bytes: int
    url_ttl: timedelta
    # What the 413 calls the files: "Attachments", "Import files".
    what: str

    def too_large(self) -> PayloadTooLargeError:
        return PayloadTooLargeError(f"{self.what} may be at most {self.max_bytes} bytes")

    def check_size(self, size: int) -> None:
        """`PayloadTooLargeError` when the declared `size` is over the limit."""
        if size > self.max_bytes:
            raise self.too_large()

    def expires_at(self) -> datetime:
        """When a URL handed out now stops working."""
        return utcnow() + self.url_ttl

    async def upload_url(self, key: str, content_type: str, size: int) -> str:
        return await self.store.upload_url(key, content_type, size, self.url_ttl)

    async def download_url(self, key: str, filename: str) -> str:
        return await self.store.download_url(key, filename, self.url_ttl)

    async def verify(self, key: str) -> ObjectInfo:
        """Called after the `PUT`: what the store actually received, which is the
        authority over what the client declared. `ConflictError` when the object
        is not there yet; `PayloadTooLargeError`, and the object removed, when it
        is bigger than allowed."""
        info = await self.store.head(key)
        if info is None:
            raise ConflictError("The file has not been uploaded yet")
        if info.size > self.max_bytes:
            await self.store.delete(key)
            raise self.too_large()
        return info
