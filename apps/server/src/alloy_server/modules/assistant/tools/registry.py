"""The toolset the agent runs, and how a tool gets on it."""

from typing import Any, Literal

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.toolsets import FilteredToolset, FunctionToolset

from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.workspaces.permissions import Permission

# Read tools are open to every member; write tools run at once; approval tools
# always pause for the user. Viewers see read tools only.
Tier = Literal["read", "write", "approval"]

toolset = FunctionToolset[AgentDeps](
    # Tools share one database session, so they must not run concurrently.
    sequential=True,
    # Strict schemas would force every optional field to be present, which turns a
    # partial update into "clear everything else".
    strict=False,
)


def read_tool(func: Any) -> Any:  # noqa: ANN401 - the decorator keeps the function's type
    return toolset.tool(metadata={"tier": "read"})(func)


def write_tool(func: Any) -> Any:  # noqa: ANN401
    return toolset.tool(metadata={"tier": "write"})(func)


def approval_tool(func: Any) -> Any:  # noqa: ANN401
    return toolset.tool(metadata={"tier": "approval"})(func)


def tool_tier(metadata: dict[str, Any] | None) -> Tier:
    tier = (metadata or {}).get("tier", "approval")
    return tier if tier in ("read", "write", "approval") else "approval"


def _visible_to(ctx: RunContext[AgentDeps], tool_def: Any) -> bool:  # noqa: ANN401
    """Viewers see read tools only, so their model never tries a write."""
    if ctx.deps.membership.can(Permission.CRM_WRITE):
        return True
    return tool_tier(tool_def.metadata) == "read"


# What the agent registers: the tools above, filtered by the caller's permission.
permitted_toolset: FilteredToolset[AgentDeps] = FilteredToolset(toolset, _visible_to)


def retry(message: str) -> ModelRetry:
    return ModelRetry(message)
