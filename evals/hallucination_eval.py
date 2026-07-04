"""Flag faithfulness scoring.

A homegrown LLM-as-judge stands in for DeepEval's hallucination metric: given the
clause text as context and a flag's risk description plus reasoning as the claim,
decide whether the claim is grounded in the clause. The hallucination rate is the
fraction of detected flags that are not grounded.
"""

from pathlib import Path

from pydantic import BaseModel

from evals.cache import DEFAULT_CACHE_DIR, CacheStats, cached_complete_json
from lexagent.bedrock import BedrockClient
from lexagent.models import Contract, Flag


class FaithfulnessDecision(BaseModel):
    is_grounded: bool
    reasoning: str


def _clause_text_for(contract: Contract, clause_id: str) -> str:
    for clause in contract.clauses:
        if clause.id == clause_id:
            return clause.text
    return ""


def _faithfulness_prompt(flag: Flag, clause_text: str) -> str:
    return (
        "Decide whether the following claim about a contract clause is fully grounded "
        "in the clause text. A claim is grounded only if the clause text actually "
        "supports it. Return is_grounded and a one-sentence reasoning.\n\n"
        f"CLAIM (risk): {flag.risk_description}\n"
        f"CLAIM (reasoning): {flag.reasoning}\n\n"
        "--- CLAUSE TEXT ---\n"
        f"{clause_text}\n"
        "--- END CLAUSE TEXT ---"
    )


def score_flag_faithfulness(
    bedrock: BedrockClient,
    flag: Flag,
    clause_text: str,
    *,
    mode: str = "auto",
    cache_dir: Path = DEFAULT_CACHE_DIR,
    stats: CacheStats | None = None,
) -> bool:
    prompt = _faithfulness_prompt(flag, clause_text)
    decision, _ = cached_complete_json(
        bedrock, prompt, FaithfulnessDecision, cache_dir=cache_dir, mode=mode, stats=stats
    )
    return decision.is_grounded


def hallucination_rate(
    bedrock: BedrockClient,
    detected: list[Flag],
    contract: Contract,
    *,
    mode: str = "auto",
    cache_dir: Path = DEFAULT_CACHE_DIR,
    stats: CacheStats | None = None,
) -> float:
    """Fraction of detected flags whose claim is not grounded in its clause."""
    if not detected:
        return 0.0
    ungrounded = 0
    for flag in detected:
        clause_text = _clause_text_for(contract, flag.clause_id)
        if not score_flag_faithfulness(
            bedrock, flag, clause_text, mode=mode, cache_dir=cache_dir, stats=stats
        ):
            ungrounded += 1
    return ungrounded / len(detected)
