"""What goes into and comes out of one agent run, and the checks made on it."""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from alloy_api.agent.tools import WRITE_TOOL_NAMES


class Prompt(BaseModel):
    text: str


class Outcome(BaseModel):
    text: str
    called: list[str]
    executed: list[str]
    paused: bool


@dataclass
class Called(Evaluator[Prompt, Outcome]):
    """The agent called one of these tools."""

    any_of: tuple[str, ...]

    def evaluate(self, ctx: EvaluatorContext[Prompt, Outcome]) -> bool:
        return any(name in ctx.output.called for name in self.any_of)


@dataclass
class Paused(Evaluator[Prompt, Outcome]):
    """The run ended waiting for approval (or did not)."""

    expected: bool = True

    def evaluate(self, ctx: EvaluatorContext[Prompt, Outcome]) -> bool:
        return ctx.output.paused is self.expected


@dataclass
class NoWriteRan(Evaluator[Prompt, Outcome]):
    """No write tool actually executed; pausing for approval is fine."""

    def evaluate(self, ctx: EvaluatorContext[Prompt, Outcome]) -> bool:
        return not any(name in WRITE_TOOL_NAMES for name in ctx.output.executed)


@dataclass
class Mentions(Evaluator[Prompt, Outcome]):
    """The reply mentions every one of these, case-insensitively."""

    words: tuple[str, ...]

    def evaluate(self, ctx: EvaluatorContext[Prompt, Outcome]) -> bool:
        text = ctx.output.text.lower()
        return all(word.lower() in text for word in self.words)


@dataclass
class Links(Evaluator[Prompt, Outcome]):
    """The reply links the record: tools return each record's `url`, which
    carries its id, and the agent is told to link records with it."""

    record_id: uuid.UUID

    def evaluate(self, ctx: EvaluatorContext[Prompt, Outcome]) -> bool:
        return str(self.record_id) in ctx.output.text
