from pydantic_ai import RunContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from alloy_server.db.base import utcnow
from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.assistant.tools.registry import read_tool
from alloy_server.modules.assistant.tools.shapes import MemberRow, WorkspaceInfo
from alloy_server.modules.workspaces.models import WorkspaceMember
from alloy_server.modules.workspaces.permissions import Permission


@read_tool
async def get_workspace(ctx: RunContext[AgentDeps]) -> WorkspaceInfo:
    """The workspace this chat belongs to, the user's role in it, today's date, and
    their time zone."""
    deps = ctx.deps
    now = utcnow().astimezone(deps.time_zone)
    return WorkspaceInfo(
        id=deps.workspace_id,
        name=deps.membership.workspace.name,
        your_role=deps.membership.role.value,
        you_can_write=deps.membership.can(Permission.CRM_WRITE),
        today=now.date().isoformat(),
        time_zone=str(deps.time_zone),
    )


@read_tool
async def list_members(ctx: RunContext[AgentDeps]) -> list[MemberRow]:
    """Who is in the workspace, by email and role. Use it to turn a name like "Bob"
    into a member when the user refers to a colleague."""
    deps = ctx.deps
    members = await deps.session.scalars(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(WorkspaceMember.workspace_id == deps.workspace_id)
        .order_by(WorkspaceMember.created_at)
    )
    return [MemberRow(user_id=m.user_id, email=m.user.email, role=m.role.value) for m in members]
