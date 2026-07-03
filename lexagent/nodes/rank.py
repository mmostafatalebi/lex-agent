"""Severity ranking node: order flags by severity, then document position."""

from lexagent.models import Flag, GraphState, Severity

_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.DEALBREAKER: 0,
    Severity.IMPORTANT: 1,
    Severity.MINOR: 2,
}


def rank(state: GraphState) -> GraphState:
    clause_order: dict[str, int] = {}
    if state.contract is not None:
        clause_order = {clause.id: index for index, clause in enumerate(state.contract.clauses)}

    def sort_key(flag: Flag) -> tuple[int, int]:
        return (
            _SEVERITY_ORDER[flag.severity],
            clause_order.get(flag.clause_id, len(clause_order)),
        )

    ordered = sorted(state.flags, key=sort_key)
    return state.model_copy(update={"flags": ordered, "status": "complete"})
