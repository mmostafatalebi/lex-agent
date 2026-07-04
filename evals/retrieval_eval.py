"""Retrieval quality scoring.

RAGAS is not importable in this environment without a langchain-family package we
do not depend on, so this ships a small deterministic scorer for the same two
metrics. For each expected flag, the referenced clause text is the query and the
taxonomy examples of the mapped clause type are the ground-truth relevant
contexts. A retrieved example counts as relevant when its clause type matches.
"""

from pathlib import Path

from evals import CATEGORY_TO_CLAUSE_TYPE
from evals.cache import DEFAULT_CACHE_DIR, RetrieveFn, make_cached_retrieve
from evals.models import ExpectedFlag, RetrievalEvalResult
from lexagent.models import ClauseType, Contract
from lexagent.nodes import normalized_contains
from lexagent.retrieve import retrieve_similar
from lexagent.taxonomy import TAXONOMY

_K = 3


def _clause_text_for_hint(contract: Contract, clause_hint: str) -> str | None:
    for clause in contract.clauses:
        haystack = " ".join(filter(None, [clause.heading, clause.section_number, clause.text]))
        if normalized_contains(haystack, clause_hint):
            return clause.text
    return None


def _relevant_count(clause_type: ClauseType) -> int:
    return sum(1 for entry in TAXONOMY if entry.clause_type is clause_type)


def evaluate_retrieval(
    fixture_name: str,
    contract: Contract,
    expected_flags: list[ExpectedFlag],
    *,
    mode: str = "auto",
    cache_dir: Path = DEFAULT_CACHE_DIR,
    retrieve: RetrieveFn | None = None,
) -> RetrievalEvalResult:
    """Score context precision and recall of retrieval across a fixture's flags."""
    real_retrieve: RetrieveFn = retrieve if retrieve is not None else retrieve_similar
    cached_retrieve = make_cached_retrieve(real_retrieve, cache_dir=cache_dir, mode=mode)

    precisions: list[float] = []
    recalls: list[float] = []

    for expected in expected_flags:
        clause_type = CATEGORY_TO_CLAUSE_TYPE.get(expected.risk_category, ClauseType.OTHER)
        query_text = _clause_text_for_hint(contract, expected.clause_hint)
        if query_text is None:
            continue

        examples = cached_retrieve(query_text, _K, clause_type)
        if not examples:
            precisions.append(0.0)
            recalls.append(0.0)
            continue

        relevant_hits = sum(1 for ex in examples if ex.clause_type is clause_type)
        total_relevant = _relevant_count(clause_type) or 1
        precisions.append(relevant_hits / len(examples))
        recalls.append(min(relevant_hits, total_relevant) / total_relevant)

    precision = sum(precisions) / len(precisions) if precisions else 0.0
    recall = sum(recalls) / len(recalls) if recalls else 0.0
    return RetrievalEvalResult(
        fixture_name=fixture_name, context_precision=precision, context_recall=recall
    )
