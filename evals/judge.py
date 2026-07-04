"""LLM-as-judge: match detected flags to expected flags and categorize risks.

Prompts are terse and rubric-driven. The risk-category vocabulary is spelled out
and the structured-output schema forces one of the allowed values. All calls go
through the response cache.
"""

from pathlib import Path

from pydantic import BaseModel

from evals import RISK_CATEGORIES
from evals.cache import DEFAULT_CACHE_DIR, CacheStats, cached_complete_json
from evals.models import ExpectedFlag
from lexagent.bedrock import BedrockClient
from lexagent.models import Flag

_VOCAB = ", ".join(RISK_CATEGORIES)


class MatchDecision(BaseModel):
    is_match: bool
    reasoning: str
    inferred_risk_category: str  # one of RISK_CATEGORIES


class CategoryDecision(BaseModel):
    category: str  # one of RISK_CATEGORIES


def _match_prompt(detected: Flag, expected: ExpectedFlag, clause_text: str) -> str:
    return (
        "Decide whether a detected contract risk and an expected contract risk refer "
        "to the SAME underlying issue in the SAME clause. Judge by the risk, not by "
        "wording.\n\n"
        "Return is_match (true only if they are the same underlying risk), a one-"
        "sentence reasoning, and inferred_risk_category for the detected risk from "
        f"this fixed list: {_VOCAB}.\n\n"
        f"EXPECTED risk category: {expected.risk_category}\n"
        f"EXPECTED clause hint: {expected.clause_hint}\n"
        f"EXPECTED quote hint: {expected.verbatim_hint}\n\n"
        f"DETECTED risk description: {detected.risk_description}\n"
        f"DETECTED quote: {detected.verbatim_quote}\n"
        f"DETECTED reasoning: {detected.reasoning}\n\n"
        "--- CLAUSE TEXT ---\n"
        f"{clause_text}\n"
        "--- END CLAUSE TEXT ---"
    )


def _category_prompt(detected: Flag, clause_text: str) -> str:
    return (
        "Assign the detected contract risk below to exactly one category from this "
        f"fixed list: {_VOCAB}. Use 'other' only when none of the specific categories "
        "fit.\n\n"
        f"DETECTED risk description: {detected.risk_description}\n"
        f"DETECTED quote: {detected.verbatim_quote}\n"
        f"DETECTED reasoning: {detected.reasoning}\n\n"
        "--- CLAUSE TEXT ---\n"
        f"{clause_text}\n"
        "--- END CLAUSE TEXT ---"
    )


def judge_flag_match(
    bedrock: BedrockClient,
    detected: Flag,
    expected: ExpectedFlag,
    clause_text: str,
    *,
    mode: str = "auto",
    cache_dir: Path = DEFAULT_CACHE_DIR,
    stats: CacheStats | None = None,
) -> MatchDecision:
    prompt = _match_prompt(detected, expected, clause_text)
    decision, _ = cached_complete_json(
        bedrock, prompt, MatchDecision, cache_dir=cache_dir, mode=mode, stats=stats
    )
    return decision


def categorize_flag(
    bedrock: BedrockClient,
    detected: Flag,
    clause_text: str,
    *,
    mode: str = "auto",
    cache_dir: Path = DEFAULT_CACHE_DIR,
    stats: CacheStats | None = None,
) -> str:
    prompt = _category_prompt(detected, clause_text)
    decision, _ = cached_complete_json(
        bedrock, prompt, CategoryDecision, cache_dir=cache_dir, mode=mode, stats=stats
    )
    category = decision.category.strip()
    return category if category in RISK_CATEGORIES else "other"
