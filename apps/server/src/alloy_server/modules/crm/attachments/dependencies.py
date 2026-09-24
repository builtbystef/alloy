from typing import Annotated

from fastapi import Depends

from alloy_server.config import SettingsDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.modules.crm.attachments.service import AttachmentStorage


def get_attachment_storage(store: ObjectStoreDep, settings: SettingsDep) -> AttachmentStorage:
    return AttachmentStorage(store, settings)


AttachmentStorageDep = Annotated[AttachmentStorage, Depends(get_attachment_storage)]
