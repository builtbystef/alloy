import uuid
from dataclasses import dataclass

from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models import Model
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alloy_server.config import Settings
from alloy_server.integrations.storage.base import ObjectStore
from alloy_server.modules.assistant.agent import (
    USAGE_LIMITS,
    agent,
    history_capability,
    model_settings,
)
from alloy_server.modules.assistant.dependencies import AgentDeps
from alloy_server.modules.workspaces.dependencies import Membership
from alloy_server.modules.workspaces.models import WorkspaceMember

from .evaluators import Outcome, Prompt
from .fixture import Fixture, member_id


@dataclass
class AgentTask:
    """Pydantic Evals calls `__call__` once per case."""

    session_factory: async_sessionmaker[AsyncSession]
    fixture: Fixture
    store: ObjectStore
    settings: Settings
    model: Model

    async def __call__(self, prompt: Prompt) -> Outcome:
        async with self.session_factory() as session:
            member = await session.get_one(WorkspaceMember, await member_id(session, self.fixture))
            await session.refresh(member, ["user", "workspace"])
            deps = AgentDeps(
                session=session,
                membership=Membership(workspace=member.workspace, member=member),
                store=self.store,
                settings=self.settings,
                request_id="evals",
                conversation_id=uuid.uuid4(),
            )
            result = await agent.run(
                prompt.text,
                deps=deps,
                model=self.model,
                model_settings=model_settings(self.settings, deps),
                usage_limits=USAGE_LIMITS,
                capabilities=[history_capability],
            )
            called: list[str] = []
            executed: list[str] = []
            for message in result.new_messages():
                for part in message.parts:
                    if isinstance(part, ToolCallPart):
                        called.append(part.tool_name)
                    elif isinstance(part, ToolReturnPart) and part.outcome == "success":
                        executed.append(part.tool_name)
            paused = isinstance(result.output, DeferredToolRequests)
            text = "" if paused else str(result.output)
            if paused:
                # What the model said before pausing, if anything.
                text = " ".join(
                    part.content
                    for message in result.new_messages()
                    if isinstance(message, ModelResponse)
                    for part in message.parts
                    if isinstance(part, TextPart)
                )
            return Outcome(text=text, called=called, executed=executed, paused=paused)
