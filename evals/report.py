"""Markdown report generation for the evaluation harness."""

from datetime import UTC, datetime

from evals.cache import CacheStats
from evals.models import FixtureReport


def _pct(value: float) -> str:
    return f"{value:.2f}"


def _check(ok: bool) -> str:
    return "✓" if ok else "✗"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _summary_table(reports: list[FixtureReport]) -> list[str]:
    lines = [
        "| Fixture | Doc Type | Precision | Recall | F1 | Hallucination "
        "| Ret. Precision | Ret. Recall |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for report in reports:
        a = report.analysis
        r = report.retrieval
        lines.append(
            f"| {a.fixture_name} | {_check(a.document_type_correct)} "
            f"| {_pct(a.precision)} | {_pct(a.recall)} | {_pct(a.f1)} "
            f"| {_pct(a.hallucination_rate)} | {_pct(r.context_precision)} "
            f"| {_pct(r.context_recall)} |"
        )
    if reports:
        doc_pct = _mean([1.0 if rep.analysis.document_type_correct else 0.0 for rep in reports])
        lines.append(
            f"| **Macro avg** | {doc_pct * 100:.0f}% "
            f"| {_pct(_mean([r.analysis.precision for r in reports]))} "
            f"| {_pct(_mean([r.analysis.recall for r in reports]))} "
            f"| {_pct(_mean([r.analysis.f1 for r in reports]))} "
            f"| {_pct(_mean([r.analysis.hallucination_rate for r in reports]))} "
            f"| {_pct(_mean([r.retrieval.context_precision for r in reports]))} "
            f"| {_pct(_mean([r.retrieval.context_recall for r in reports]))} |"
        )
    return lines


def _fixture_detail(report: FixtureReport) -> list[str]:
    a = report.analysis
    expected_type = "matched" if a.document_type_correct else "mismatched"
    lines = [
        f"### {a.fixture_name}",
        "",
        f"Document type {expected_type} {_check(a.document_type_correct)}",
        "",
        f"Expected {report.expected_count} flags, detected {report.detected_count} flags, "
        f"matched {report.matched_count}.",
        "",
        "| Expected | Detected | Match | Notes |",
        "|---|---|---|---|",
    ]
    unmatched_detected = []
    for match in a.matches:
        if match.expected is not None:
            exp = match.expected
            expected_cell = (
                f"{exp.clause_hint} / {exp.risk_category} / {exp.expected_severity.value}"
            )
            if match.detected is not None:
                det = match.detected
                quote = det.verbatim_quote.strip().replace("\n", " ")[:48]
                detected_cell = f'{det.clause_id} / "{quote}" / {det.severity.value}'
            else:
                detected_cell = "(not detected)"
            lines.append(
                f"| {expected_cell} | {detected_cell} | {_check(match.is_match)} "
                f"| {match.match_reasoning} |"
            )
        elif match.detected is not None:
            det = match.detected
            quote = det.verbatim_quote.strip().replace("\n", " ")[:48]
            unmatched_detected.append(f'- {det.clause_id} / "{quote}"')

    if unmatched_detected:
        lines.append("")
        lines.append("Detected but unmatched:")
        lines.extend(unmatched_detected)
    lines.append("")
    return lines


def render_report(
    reports: list[FixtureReport],
    *,
    cache_mode: str = "replay",
    stats: CacheStats | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Render the full Markdown evaluation report."""
    when = (generated_at or datetime.now(UTC)).astimezone(UTC)
    timestamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    cached = stats.hits if stats is not None else 0
    live = stats.live_calls if stats is not None else 0
    cost = stats.total_cost_usd if stats is not None else 0.0

    lines = [
        "# LexAgent Evaluation Report",
        "",
        f"Generated: {timestamp}",
        f"Cache mode: {cache_mode}",
        f"Total cost: ${cost:.4f} (cached: {cached} calls, live: {live})",
        "",
        "## Summary",
        "",
    ]
    lines.extend(_summary_table(reports))
    lines.append("")
    lines.append("## Per-fixture detail")
    lines.append("")
    for report in reports:
        lines.extend(_fixture_detail(report))
    return "\n".join(lines).rstrip() + "\n"
