from typing import Annotated

from fastapi import Depends

from alloy_server.config import SettingsDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.integrations.storage.uploads import UploadStore


def get_chat_upload_store(objects: ObjectStoreDep, settings: SettingsDep) -> UploadStore:
    """A file sent to the assistant can become an attachment, so it is held to the
    same limit."""
    return UploadStore(objects, settings.attachment_max_bytes, settings.storage_url_ttl, "Files")


ChatUploadStoreDep = Annotated[UploadStore, Depends(get_chat_upload_store)]
