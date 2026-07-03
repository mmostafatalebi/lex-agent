"""Redline drafting node: one LLM call per accepted flag.

Rejected flags produce no redlines. Each draft's ``original_text`` is gated by a
substring check against the source clause, with one stricter-prompt retry before
the draft is dropped. A single bad draft never crashes the run.
"""

import logging

from lexagent.bedrock import BedrockClient
from lexagent.models import Clause, Contract, Flag, GraphState, Redline, RedlineDraft
from lexagent.nodes import normalized_contains
from lexagent.prompts import draft_redline_prompt

logger = logging.getLogger(__name__)

_STRICTER_HINT = (
    "The original_text must be a character-for-character substring of the clause "
    "text. Do not paraphrase, summarize, or alter punctuation or spacing."
)


def _get_clause(contract: Contract | None, clause_id: str) -> Clause | None:
    if contract is None:
        return None
    for clause in contract.clauses:
        if clause.id == clause_id:
            return clause
    return None


def _draft_one(
    bedrock: BedrockClient, clause: Clause, flag: Flag
) -> tuple[Redline | None, float]:
    prompt = draft_redline_prompt(clause, flag)
    cost = 0.0

    draft, usage = bedrock.complete_json(prompt, RedlineDraft)
    cost += usage.total_cost_usd
    if not normalized_contains(clause.text, draft.original_text):
        draft, usage = bedrock.complete_json(prompt, RedlineDraft, system=_STRICTER_HINT)
        cost += usage.total_cost_usd
        if not normalized_contains(clause.text, draft.original_text):
            logger.warning(
                "Dropping redline on %s: original_text %r is not a substring of the clause",
                clause.id,
                draft.original_text[:60],
            )
            return None, cost

    redline = Redline(
        id=f"redline_{flag.id}",
        clause_id=clause.id,
        flag_id=flag.id,
        original_text=draft.original_text,
        revised_text=draft.revised_text,
        justification=draft.justification,
    )
    return redline, cost


def draft_redlines(state: GraphState, bedrock: BedrockClient) -> GraphState:
    """Generate a redline for every accepted flag. Reject-decisions produce no redlines."""
    accepted_flag_ids = {
        decision.flag_id for decision in state.human_decisions if decision.decision == "accept"
    }
    accepted_flags = [flag for flag in state.flags if flag.id in accepted_flag_ids]

    redlines: list[Redline] = []
    cost = 0.0
    for flag in accepted_flags:
        clause = _get_clause(state.contract, flag.clause_id)
        if clause is None:
            logger.warning("Skipping redline for %s: clause %s not found", flag.id, flag.clause_id)
            continue
        redline, clause_cost = _draft_one(bedrock, clause, flag)
        cost += clause_cost
        if redline is not None:
            redlines.append(redline)

    return state.model_copy(
        update={"redlines": redlines, "total_cost_usd": state.total_cost_usd + cost}
    )
