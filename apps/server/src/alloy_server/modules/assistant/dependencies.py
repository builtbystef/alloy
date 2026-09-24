from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, status
from pydantic_ai import CustomEvent

from alloy_server.config import SettingsDep
from alloy_server.integrations.ai import create_model

if TYPE_CHECKING:
    from uuid import UUID

    from pydantic_ai.models import Model
    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_server.config import Settings
    from alloy_server.integrations.storage import ObjectStore
    from alloy_server.modules.workspaces.dependencies import Membership


@dataclass(kw_only=True)
class ApprovalPreviewEvent(CustomEvent):
    """What a paused tool call is about to do, for the approval card: a title and a
    few columns of rows. Sent to the browser as a `data-approval_preview` part and
    kept on the response's metadata, so a reload shows the same table. The
    `tool_call_id` is the envelope's, set by `emit` inside the tool."""

    title: str
    columns: list[str]
    rows: list[list[str]]
    total: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "title": self.title,
            "columns": self.columns,
            "rows": self.rows,
            "total": self.total,
        }


@dataclass(slots=True)
class AgentDeps:
    session: AsyncSession
    membership: Membership
    store: ObjectStore
    settings: Settings
    request_id: str
    conversation_id: UUID
    time_zone: ZoneInfo = field(default_factory=lambda: ZoneInfo("UTC"))
    # Filled by tools that pause for approval; saved with the response.
    approval_previews: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def workspace_id(self) -> UUID:
        return self.membership.workspace.id

    def record_url(self, kind: str, record_id: UUID) -> str:
        base = str(self.settings.frontend_url).rstrip("/")
        return f"{base}/{self.workspace_id}/{kind}/{record_id}"

    def download_url(self, attachment_id: UUID) -> str:
        base = str(self.settings.frontend_url).rstrip("/")
        return f"{base}/api/workspaces/{self.workspace_id}/attachments/{attachment_id}/download"


def get_model(settings: SettingsDep) -> Model:
    """The configured model; 503 when no key is set. Tests override it with a
    scripted model."""
    model = create_model(settings)
    if model is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The assistant is not configured: set ALLOY_OPENAI_API_KEY",
        )
    return model


ModelDep = Annotated["Model", Depends(get_model)]
