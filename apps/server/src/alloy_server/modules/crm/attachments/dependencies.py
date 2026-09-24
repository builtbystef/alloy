from typing import Annotated

from fastapi import Depends

from alloy_server.config import SettingsDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.integrations.storage.uploads import UploadStorage


def get_attachment_storage(store: ObjectStoreDep, settings: SettingsDep) -> UploadStorage:
    return UploadStorage(
        store, settings.attachment_max_bytes, settings.storage_url_ttl, "Attachments"
    )


AttachmentStorageDep = Annotated[UploadStorage, Depends(get_attachment_storage)]
