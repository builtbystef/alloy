from typing import Annotated

from fastapi import Depends

from alloy_server.dependencies import ObjectStoreDep, SettingsDep
from alloy_server.integrations.storage.uploads import UploadStore


def get_attachment_store(objects: ObjectStoreDep, settings: SettingsDep) -> UploadStore:
    return UploadStore(
        objects, settings.attachment_max_bytes, settings.storage_url_ttl, "Attachments"
    )


AttachmentStoreDep = Annotated[UploadStore, Depends(get_attachment_store)]
