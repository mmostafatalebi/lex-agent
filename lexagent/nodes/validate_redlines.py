"""Final citation gate: drop redlines whose original_text is not a substring.

A safety net after ``draft_redlines`` (which already retries once). The substring
check is NFKC-normalized to avoid smart-quote and ligature false positives.
"""

import logging

from lexagent.models import Clause, Contract, GraphState, Redline
from lexagent.nodes import normalized_contains

logger = logging.getLogger(__name__)


def _get_clause(contract: Contract | None, clause_id: str) -> Clause | None:
    if contract is None:
        return None
    for clause in contract.clauses:
        if clause.id == clause_id:
            return clause
    return None


def validate_redlines(state: GraphState) -> GraphState:
    valid: list[Redline] = []
    for redline in state.redlines:
        clause = _get_clause(state.contract, redline.clause_id)
        if clause is not None and normalized_contains(clause.text, redline.original_text):
            valid.append(redline)
        else:
            logger.warning(
                "Dropping redline %s: original_text is not a substring of clause %s",
                redline.id,
                redline.clause_id,
            )

    return state.model_copy(update={"redlines": valid, "status": "complete"})
