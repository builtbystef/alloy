import uuid
from typing import TYPE_CHECKING

from pydantic_ai import RunContext

from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.assistant.tools.common import (
    attach,
    attachment_row,
    attachments_of,
    chat_uploads,
    check_bulk,
    owned,
    owned_all,
    pause_for_approval,
    plural,
    write_allowed,
)
from alloy_server.modules.assistant.tools.registry import (
    approval_tool,
    read_tool,
    retry,
    write_tool,
)
from alloy_server.modules.assistant.tools.shapes import AttachmentRow, Deleted, FileTarget
from alloy_server.modules.crm.attachments import service as attachment_service
from alloy_server.modules.crm.attachments.models import Attachment
from alloy_server.modules.crm.companies.models import Company
from alloy_server.modules.crm.contacts.models import Contact

if TYPE_CHECKING:
    from uuid import UUID


async def _parent(
    deps: AgentDeps, contact_id: UUID | None, company_id: UUID | None
) -> Contact | Company:
    """The one record named by exactly one of the two ids."""
    if contact_id is not None and company_id is None:
        return await owned(deps, Contact, contact_id)
    if company_id is not None and contact_id is None:
        return await owned(deps, Company, company_id)
    raise retry("Pass exactly one of contact_id and company_id.")


@read_tool
async def list_attachments(
    ctx: RunContext[AgentDeps],
    *,
    contact_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
) -> list[AttachmentRow]:
    """Files attached to a contact or a company, newest first, with download links.
    Pass exactly one of `contact_id` and `company_id`."""
    return await attachments_of(ctx.deps, await _parent(ctx.deps, contact_id, company_id))


@write_tool
async def attach_files(ctx: RunContext[AgentDeps], items: list[FileTarget]) -> list[AttachmentRow]:
    """Attach files the user dropped into this chat to existing contacts or companies.
    Each item names one upload and exactly one of `contact_id` or `company_id`. One
    item runs at once; more than one pauses for approval."""
    write_allowed(ctx)
    check_bulk(items)
    deps = ctx.deps
    uploads = await chat_uploads(deps, [item.upload_id for item in items])
    parents = [await _parent(deps, item.contact_id, item.company_id) for item in items]
    if len(items) > 1:
        await pause_for_approval(
            ctx,
            title=f"Attach {plural(len(items), 'file')}",
            columns=["File", "To"],
            rows=[[u.filename, p.name] for u, p in zip(uploads, parents, strict=True)],
        )
    attached = [attach(deps, u, p) for u, p in zip(uploads, parents, strict=True)]
    await deps.session.commit()
    return [attachment_row(deps, a) for a in attached]


@approval_tool
async def delete_attachments(
    ctx: RunContext[AgentDeps], attachment_ids: list[uuid.UUID]
) -> Deleted:
    """Delete attached files. Always pauses for the user's approval."""
    write_allowed(ctx)
    deps = ctx.deps
    attachments = await owned_all(deps, Attachment, attachment_ids)
    await pause_for_approval(
        ctx,
        title=f"Delete {plural(len(attachments), 'file')}",
        columns=["File", "Size"],
        rows=[[a.filename, f"{a.size} bytes"] for a in attachments],
    )
    names = [a.filename for a in attachments]
    for attachment in attachments:
        await attachment_service.delete_attachment(
            deps.session, deps.store, deps.membership, attachment.id
        )
    return Deleted(deleted=names)
