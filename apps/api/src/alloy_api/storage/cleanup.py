import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from uuid import UUID

    from alloy_api.storage.base import ObjectStore

logger = logging.getLogger(__name__)


def storage_prefix(workspace_id: UUID) -> str:
    """Every object of a workspace lives under this, so deleting the workspace can
    clear its storage by prefix."""
    return f"workspaces/{workspace_id}/"


async def delete_stored(
    store: ObjectStore, *, keys: Iterable[str] = (), prefixes: Iterable[str] = ()
) -> None:
    """Best effort, after the rows are committed. Call with what the transaction
    removed."""
    for key in keys:
        try:
            await store.delete(key)
        except Exception:
            logger.exception("Could not delete stored object %s", key)
    for prefix in prefixes:
        try:
            await store.delete_prefix(prefix)
        except Exception:
            logger.exception("Could not delete stored objects under %s", prefix)
