"""Clause classification node: one batched Bedrock call over all clauses."""

from pydantic import BaseModel

from lexagent.bedrock import BedrockClient, BedrockValidationError
from lexagent.models import Clause, ClauseType, GraphState
from lexagent.prompts import classify_clauses_prompt

_STRICTER_HINT = (
    "Only classify the clause_ids provided. Echo each clause_id exactly as given. "
    "Do not invent new clause_ids."
)


class ClauseClassificationEntry(BaseModel):
    clause_id: str
    clause_type: ClauseType


class ClauseClassificationBatch(BaseModel):
    classifications: list[ClauseClassificationEntry]


def classify_clauses(state: GraphState, bedrock: BedrockClient) -> GraphState:
    contract = state.contract
    if contract is None:
        raise ValueError("classify_clauses requires an ingested contract")

    valid_ids = {clause.id for clause in contract.clauses}
    system: str | None = None
    mapping: dict[str, ClauseType] = {}
    extra: set[str] = set()
    cost = 0.0

    for _ in range(2):
        prompt = classify_clauses_prompt(contract.document_type, contract.clauses)
        result, usage = bedrock.complete_json(prompt, ClauseClassificationBatch, system=system)
        cost += usage.total_cost_usd

        returned_ids = {entry.clause_id for entry in result.classifications}
        extra = returned_ids - valid_ids
        if not extra:
            mapping = {entry.clause_id: entry.clause_type for entry in result.classifications}
            break
        system = _STRICTER_HINT
    else:
        raise BedrockValidationError(
            f"Clause classification returned unknown clause_ids: {sorted(extra)}"
        )

    new_clauses: list[Clause] = [
        clause.model_copy(update={"clause_type": mapping.get(clause.id, ClauseType.OTHER)})
        for clause in contract.clauses
    ]
    new_contract = contract.model_copy(update={"clauses": new_clauses})
    return state.model_copy(
        update={
            "contract": new_contract,
            "total_cost_usd": state.total_cost_usd + cost,
        }
    )
