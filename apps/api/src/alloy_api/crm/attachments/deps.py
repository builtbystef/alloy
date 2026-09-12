from typing import Annotated

from fastapi import Depends

from alloy_api.config import SettingsDep
from alloy_api.crm.attachments.service import AttachmentStorage
from alloy_api.integrations.storage import ObjectStoreDep


def get_attachment_storage(store: ObjectStoreDep, settings: SettingsDep) -> AttachmentStorage:
    return AttachmentStorage(store, settings)


AttachmentStorageDep = Annotated[AttachmentStorage, Depends(get_attachment_storage)]
