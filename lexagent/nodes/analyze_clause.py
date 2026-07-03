"""Per-clause risk analysis node.

For each substantive clause, retrieve taxonomy examples, ask the model for risk
flags grounded in those examples, and keep only flags whose supporting quote is a
literal substring of the clause text.
"""

import logging

from pydantic import BaseModel

from lexagent.bedrock import BedrockClient
from lexagent.models import Clause, ClauseType, DocumentType, Flag, GraphState, Severity
from lexagent.nodes import normalized_contains
from lexagent.prompts import analyze_clause_prompt
from lexagent.retrieve import retrieve_similar

logger = logging.getLogger(__name__)

_STRICTER_HINT = (
    "Every verbatim_quote must be a character-for-character substring of the clause "
    "text. Do not paraphrase, do not summarize, do not alter punctuation or spacing."
)


class FlagDraft(BaseModel):
    risk_description: str
    severity: Severity
    verbatim_quote: str
    reasoning: str


class AnalysisResult(BaseModel):
    flags: list[FlagDraft]


def _is_substantive(clause: Clause) -> bool:
    return clause.clause_type is not None and clause.clause_type is not ClauseType.OTHER


def _gate(
    drafts: list[FlagDraft], clause_text: str
) -> tuple[list[FlagDraft], list[FlagDraft]]:
    good = [d for d in drafts if normalized_contains(clause_text, d.verbatim_quote)]
    bad = [d for d in drafts if not normalized_contains(clause_text, d.verbatim_quote)]
    return good, bad


def _analyze_single(
    clause: Clause,
    document_type: DocumentType,
    bedrock: BedrockClient,
) -> tuple[list[Flag], float]:
    examples = retrieve_similar(clause.text, k=3, clause_type=clause.clause_type)
    canonical = [e for e in examples if not e.is_risky]
    risky = [e for e in examples if e.is_risky]
    prompt = analyze_clause_prompt(document_type, clause, canonical, risky)

    cost = 0.0
    result, usage = bedrock.complete_json(prompt, AnalysisResult)
    cost += usage.total_cost_usd
    good, bad = _gate(result.flags, clause.text)

    if bad:
        result, usage = bedrock.complete_json(prompt, AnalysisResult, system=_STRICTER_HINT)
        cost += usage.total_cost_usd
        good, bad = _gate(result.flags, clause.text)
        for draft in bad:
            logger.warning(
                "Dropping flag on %s: verbatim_quote %r is not a substring of the clause",
                clause.id,
                draft.verbatim_quote[:60],
            )

    flags = [
        Flag(
            id=f"flag_{clause.id}_{index:03d}",
            clause_id=clause.id,
            risk_description=draft.risk_description,
            severity=draft.severity,
            verbatim_quote=draft.verbatim_quote,
            reasoning=draft.reasoning,
        )
        for index, draft in enumerate(good, start=1)
    ]
    return flags, cost


def analyze_clause(state: GraphState, bedrock: BedrockClient) -> GraphState:
    contract = state.contract
    if contract is None:
        raise ValueError("analyze_clause requires a classified contract")

    all_flags: list[Flag] = []
    cost = 0.0
    for clause in contract.clauses:
        if not _is_substantive(clause):
            continue
        flags, clause_cost = _analyze_single(clause, contract.document_type, bedrock)
        all_flags.extend(flags)
        cost += clause_cost

    return state.model_copy(
        update={
            "flags": all_flags,
            "total_cost_usd": state.total_cost_usd + cost,
        }
    )
