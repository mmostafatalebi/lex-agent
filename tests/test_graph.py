import re
from pathlib import Path
from typing import Any

from lexagent.bedrock import BedrockValidationError
from lexagent.graph import run_analysis
from lexagent.models import ClauseType, DocumentType, Severity
from lexagent.nodes.analyze_clause import AnalysisResult, FlagDraft
from lexagent.nodes.classify_clauses import ClauseClassificationBatch, ClauseClassificationEntry
from lexagent.nodes.classify_document import DocumentClassification
from tests.conftest import make_usage

_CLAUSE_TEXT = re.compile(
    r"--- BEGIN CLAUSE TEXT ---\n(.*)\n--- END CLAUSE TEXT ---", re.DOTALL
)


def _dispatch(flags_per_clause: int) -> Any:
    """Build a complete_json side effect keyed on the requested schema."""

    def side_effect(
        prompt: str,
        schema: type,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> tuple[Any, Any]:
        if schema is DocumentClassification:
            return (
                DocumentClassification(document_type=DocumentType.MSA, reasoning="msa"),
                make_usage(),
            )
        if schema is ClauseClassificationBatch:
            ids = re.findall(r"\[(clause_\d+)\]", prompt)
            entries = [
                ClauseClassificationEntry(clause_id=cid, clause_type=ClauseType.LIABILITY)
                for cid in ids
            ]
            return ClauseClassificationBatch(classifications=entries), make_usage()
        if schema is AnalysisResult:
            match = _CLAUSE_TEXT.search(prompt)
            assert match is not None
            clause_text = match.group(1)
            drafts = [
                FlagDraft(
                    risk_description="Risk found in clause",
                    severity=Severity.IMPORTANT,
                    verbatim_quote=clause_text[:40],
                    reasoning="Grounded in a verbatim substring.",
                )
                for _ in range(flags_per_clause)
            ]
            return AnalysisResult(flags=drafts), make_usage()
        raise AssertionError(f"unexpected schema: {schema}")

    return side_effect


def test_end_to_end_produces_grounded_flags(
    sample_msa_pdf: Path, fake_bedrock_client: Any, mock_retrieve_similar: Any
) -> None:
    fake_bedrock_client.complete_json.side_effect = _dispatch(flags_per_clause=1)
    state = run_analysis(sample_msa_pdf, bedrock=fake_bedrock_client)

    assert state.status == "complete"
    assert state.contract is not None
    assert len(state.flags) >= 5

    text_by_id = {c.id: c.text for c in state.contract.clauses}
    for flag in state.flags:
        assert flag.clause_id in text_by_id
        assert flag.verbatim_quote in text_by_id[flag.clause_id]


def test_zero_flags_for_clause_does_not_crash(
    sample_msa_pdf: Path, fake_bedrock_client: Any, mock_retrieve_similar: Any
) -> None:
    fake_bedrock_client.complete_json.side_effect = _dispatch(flags_per_clause=0)
    state = run_analysis(sample_msa_pdf, bedrock=fake_bedrock_client)
    assert state.status == "complete"
    assert state.flags == []


def test_classify_document_failure_marks_run_failed(
    sample_msa_pdf: Path, fake_bedrock_client: Any, mock_retrieve_similar: Any
) -> None:
    fake_bedrock_client.complete_json.side_effect = BedrockValidationError("schema mismatch")
    state = run_analysis(sample_msa_pdf, bedrock=fake_bedrock_client)

    assert state.status == "failed"
    assert state.error is not None
    assert "classify_document" in state.error
    assert state.flags == []
