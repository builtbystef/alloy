from typing import Annotated

from fastapi import Depends

from alloy_server.config import SettingsDep
from alloy_server.integrations.storage import ObjectStoreDep
from alloy_server.integrations.storage.uploads import UploadStorage


def get_import_storage(store: ObjectStoreDep, settings: SettingsDep) -> UploadStorage:
    return UploadStorage(store, settings.import_max_bytes, settings.storage_url_ttl, "Import files")


ImportStorageDep = Annotated[UploadStorage, Depends(get_import_storage)]
