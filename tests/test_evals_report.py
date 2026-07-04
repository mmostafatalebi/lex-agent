import re
from datetime import UTC, datetime

from evals.models import AnalysisEvalResult, FixtureReport, RetrievalEvalResult
from evals.report import render_report


def _fixture_report(name: str, f1: float) -> FixtureReport:
    analysis = AnalysisEvalResult(
        fixture_name=name,
        precision=f1,
        recall=f1,
        f1=f1,
        document_type_correct=True,
        matches=[],
        hallucination_rate=0.1,
    )
    retrieval = RetrievalEvalResult(
        fixture_name=name, context_precision=0.8, context_recall=0.7
    )
    return FixtureReport(
        analysis=analysis,
        retrieval=retrieval,
        detected_count=5,
        expected_count=6,
        matched_count=4,
    )


def _reports() -> list[FixtureReport]:
    return [
        _fixture_report("msa_problematic", 0.80),
        _fixture_report("nda_broad_scope", 0.70),
        _fixture_report("sow_ambiguous", 0.60),
    ]


def test_report_has_header_and_summary_table() -> None:
    markdown = render_report(_reports())
    assert markdown.startswith("# LexAgent Evaluation Report")
    assert "## Summary" in markdown
    for name in ("msa_problematic", "nda_broad_scope", "sow_ambiguous"):
        assert name in markdown
    assert "**Macro avg**" in markdown


def test_macro_average_is_mean_of_f1() -> None:
    markdown = render_report(_reports())
    expected_macro = (0.80 + 0.70 + 0.60) / 3
    macro_line = next(line for line in markdown.splitlines() if "**Macro avg**" in line)
    assert f"{expected_macro:.2f}" in macro_line


def test_timestamp_is_utc_iso() -> None:
    when = datetime(2026, 7, 15, 12, 34, 56, tzinfo=UTC)
    markdown = render_report(_reports(), generated_at=when)
    assert "Generated: 2026-07-15T12:34:56Z" in markdown
    match = re.search(r"Generated: (\S+)", markdown)
    assert match is not None
    assert match.group(1).endswith("Z")
