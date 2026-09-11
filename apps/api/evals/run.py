"""Run the agent evals against the live model.

uv run python -m evals.run [--judge]
"""

import argparse
import asyncio
from typing import Any

from pydantic_evals import Dataset
from pydantic_evals.evaluators import Evaluator, LLMJudge

from alloy_api.agent.agent import build_model
from alloy_api.db import create_database_state
from alloy_api.storage.memory import MemoryObjectStore

from .cases import cases
from .db import migrate, use_eval_database
from .evaluators import Outcome, Prompt
from .fixture import seed, teardown
from .task import AgentTask


async def main(*, judge: bool) -> None:
    settings = use_eval_database()
    model = build_model(settings)
    if model is None:
        msg = "Set ALLOY_OPENAI_API_KEY to run the evals"
        raise SystemExit(msg)
    state = create_database_state(settings)
    await migrate(state["engine"])
    session_factory = state["session_factory"]
    async with session_factory() as session:
        fixture = await seed(session)
    try:
        task = AgentTask(
            session_factory=session_factory,
            fixture=fixture,
            # No case uploads a file, so nothing needs the real bucket.
            store=MemoryObjectStore(),
            settings=settings,
            model=model,
        )
        evaluators: list[Evaluator[Prompt, Outcome, Any]] = []
        if judge:
            evaluators.append(
                LLMJudge(
                    rubric="The reply is short, answers the prompt directly, does not invent "
                    "records, and links or names the records it refers to.",
                    model=model,
                    include_input=True,
                )
            )
        dataset = Dataset(name="alloy-agent", cases=cases(fixture), evaluators=evaluators)
        report = await dataset.evaluate(task, max_concurrency=1)
        report.print(include_input=True, include_output=False)
    finally:
        async with session_factory() as session:
            await teardown(session, fixture)
        await state["engine"].dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--judge", action="store_true", help="add an LLM judge on every reply")
    args = parser.parse_args()
    asyncio.run(main(judge=args.judge))
