from typing import Annotated

from fastapi import Depends

from alloy_server.config import SettingsDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.integrations.storage.uploads import UploadStorage


def get_chat_upload_storage(store: ObjectStoreDep, settings: SettingsDep) -> UploadStorage:
    """A file sent to the assistant can become an attachment, so it is held to the
    same limit."""
    return UploadStorage(store, settings.attachment_max_bytes, settings.storage_url_ttl, "Files")


ChatUploadStorageDep = Annotated[UploadStorage, Depends(get_chat_upload_storage)]
