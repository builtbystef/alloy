"""The assistant's tools, one module per CRM domain. Importing the package
registers every tool on `toolset`; `permitted_toolset` is what the agent runs."""

from alloy_server.modules.assistant.tools import (  # noqa: F401 - registers the tools
    activities,
    attachments,
    companies,
    contacts,
    tasks,
    workspace,
)
from alloy_server.modules.assistant.tools.registry import permitted_toolset, tool_tier, toolset

WRITE_TOOL_NAMES = frozenset(
    name for name, tool in toolset.tools.items() if tool_tier(tool.metadata) != "read"
)

__all__ = ["WRITE_TOOL_NAMES", "permitted_toolset", "toolset"]
