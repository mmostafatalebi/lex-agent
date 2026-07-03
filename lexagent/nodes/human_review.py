"""Human review node: pause the graph for accept/reject decisions.

Calls ``interrupt()`` with the current flags. LangGraph checkpoints the state and
raises ``GraphInterrupt``; when the graph is resumed with ``Command(resume=...)``,
the ``interrupt()`` call returns that value at exactly this line and execution
continues.
"""

from typing import Any

from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict

from lexagent.models import Flag, GraphState, HumanDecision


class HumanReviewPayload(BaseModel):
    """The payload passed to interrupt() so the caller knows what to review."""

    model_config = ConfigDict(frozen=True)

    flags: list[Flag]
    instructions: str = (
        "Review each flag and provide accept or reject for every flag_id. "
        "Resume by calling the graph with Command(resume=<list of HumanDecision>)."
    )


def human_review(state: GraphState) -> GraphState:
    """Pause the graph for human review. On resume, applies the decisions to state."""
    payload = HumanReviewPayload(flags=state.flags)
    decisions_data: Any = interrupt(payload.model_dump())

    if not isinstance(decisions_data, list):
        raise ValueError("Resume payload must be a list of HumanDecision objects")
    decisions = [HumanDecision.model_validate(item) for item in decisions_data]

    flag_ids = {flag.id for flag in state.flags}
    for decision in decisions:
        if decision.flag_id not in flag_ids:
            raise ValueError(f"Unknown flag_id in resume payload: {decision.flag_id}")

    return state.model_copy(
        update={"human_decisions": decisions, "status": "drafting"}
    )
