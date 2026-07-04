"""Analysis pipeline evaluation.

Runs the real analysis graph against a fixture (LLM calls and retrieval routed
through the response cache), matches detected flags to expected flags with the
judge, and scores precision, recall, F1, document-type correctness, and the
hallucination rate.
"""

from pathlib import Path
from typing import TypeVar
from unittest.mock import patch

from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from evals.cache import DEFAULT_CACHE_DIR, CacheStats, RetrieveFn, cached_complete_json
from evals.hallucination_eval import hallucination_rate
from evals.judge import judge_flag_match
from evals.models import AnalysisEvalResult, ExpectedFlag, FixtureCase, FixtureReport, FlagMatch
from evals.retrieval_eval import evaluate_retrieval
from lexagent.bedrock import BedrockClient, TokenUsage
from lexagent.graph import run_analysis
from lexagent.models import Contract, Flag
from lexagent.retrieve import retrieve_similar

_T = TypeVar("_T", bound=BaseModel)


class CachingBedrockClient(BedrockClient):
    """A BedrockClient whose complete_json is routed through the response cache."""

    def __init__(
        self, real: BedrockClient, cache_dir: Path, mode: str, stats: CacheStats
    ) -> None:
        self._real = real
        self._cache_dir = cache_dir
        self._mode = mode
        self._stats = stats

    def complete_json(
        self,
        prompt: str,
        schema: type[_T],
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> tuple[_T, TokenUsage]:
        return cached_complete_json(
            self._real,
            prompt,
            schema,
            system=system,
            cache_dir=self._cache_dir,
            mode=self._mode,
            stats=self._stats,
        )


def _clause_text_for(contract: Contract, clause_id: str) -> str:
    for clause in contract.clauses:
        if clause.id == clause_id:
            return clause.text
    return ""


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _match_flags(
    real_bedrock: BedrockClient,
    detected: list[Flag],
    expected_flags: list[ExpectedFlag],
    contract: Contract,
    *,
    mode: str,
    cache_dir: Path,
    stats: CacheStats,
) -> tuple[list[FlagMatch], set[str]]:
    matches: list[FlagMatch] = []
    matched_detected: set[str] = set()

    for expected in expected_flags:
        found: Flag | None = None
        reasoning = "No detected flag matched this expected risk."
        for candidate in detected:
            if candidate.id in matched_detected:
                continue
            decision = judge_flag_match(
                real_bedrock,
                candidate,
                expected,
                _clause_text_for(contract, candidate.clause_id),
                mode=mode,
                cache_dir=cache_dir,
                stats=stats,
            )
            if decision.is_match:
                found = candidate
                reasoning = decision.reasoning
                break
        if found is not None:
            matched_detected.add(found.id)
        matches.append(
            FlagMatch(
                expected=expected,
                detected=found,
                is_match=found is not None,
                match_reasoning=reasoning,
            )
        )

    for candidate in detected:
        if candidate.id not in matched_detected:
            matches.append(
                FlagMatch(
                    expected=None,
                    detected=candidate,
                    is_match=False,
                    match_reasoning="Detected but not matched to any expected risk.",
                )
            )

    return matches, matched_detected


def evaluate_analysis(
    case: FixtureCase,
    real_bedrock: BedrockClient,
    *,
    mode: str = "auto",
    cache_dir: Path = DEFAULT_CACHE_DIR,
    stats: CacheStats | None = None,
    retrieve: RetrieveFn | None = None,
) -> AnalysisEvalResult:
    """Run the pipeline against one fixture and score flag detection."""
    stats = stats if stats is not None else CacheStats()
    caching = CachingBedrockClient(real_bedrock, cache_dir, mode, stats)

    from evals.cache import make_cached_retrieve

    real_retrieve: RetrieveFn = retrieve if retrieve is not None else retrieve_similar
    cached_retrieve = make_cached_retrieve(real_retrieve, cache_dir=cache_dir, mode=mode)

    with patch("lexagent.nodes.analyze_clause.retrieve_similar", cached_retrieve):
        out = run_analysis(
            case.contract_path,
            thread_id=f"eval_{case.name}",
            bedrock=caching,
            checkpointer=MemorySaver(),
        )

    if out.get("status") == "failed":
        raise RuntimeError(f"Analysis failed on {case.name}: {out.get('error')}")

    contract = out["contract"]
    detected: list[Flag] = list(out["flags"])

    matches, matched_detected = _match_flags(
        real_bedrock, detected, case.expected_flags, contract,
        mode=mode, cache_dir=cache_dir, stats=stats,
    )

    matched_count = len(matched_detected)
    precision = matched_count / len(detected) if detected else 0.0
    recall = matched_count / len(case.expected_flags) if case.expected_flags else 0.0
    halluc = hallucination_rate(
        real_bedrock, detected, contract, mode=mode, cache_dir=cache_dir, stats=stats
    )

    return AnalysisEvalResult(
        fixture_name=case.name,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        document_type_correct=contract.document_type == case.expected_document_type,
        matches=matches,
        hallucination_rate=halluc,
    )


def run_fixture(
    case: FixtureCase,
    real_bedrock: BedrockClient,
    *,
    mode: str = "auto",
    cache_dir: Path = DEFAULT_CACHE_DIR,
    stats: CacheStats | None = None,
    retrieve: RetrieveFn | None = None,
) -> FixtureReport:
    """Score both analysis and retrieval for one fixture."""
    stats = stats if stats is not None else CacheStats()
    analysis = evaluate_analysis(
        case, real_bedrock, mode=mode, cache_dir=cache_dir, stats=stats, retrieve=retrieve
    )
    detected_count = sum(1 for m in analysis.matches if m.detected is not None)
    matched_count = sum(1 for m in analysis.matches if m.is_match)

    # Retrieval needs the parsed contract; re-parse via the same pipeline entry.
    contract = _parse_contract(case)
    retrieval = evaluate_retrieval(
        case.name, contract, case.expected_flags, mode=mode, cache_dir=cache_dir, retrieve=retrieve
    )

    return FixtureReport(
        analysis=analysis,
        retrieval=retrieval,
        detected_count=detected_count,
        expected_count=len(case.expected_flags),
        matched_count=matched_count,
    )


def _parse_contract(case: FixtureCase) -> Contract:
    from lexagent.parse import parse_docx, parse_pdf

    path = case.contract_path
    if path.suffix.lower() == ".pdf":
        return parse_pdf(path)
    return parse_docx(path)
