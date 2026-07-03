from pathlib import Path
from typing import Any

from lexagent.bedrock import BedrockValidationError
from lexagent.graph import run_analysis
from tests.conftest import make_analysis_dispatch


def test_analysis_pauses_at_review_with_grounded_flags(
    sample_msa_pdf: Path,
    fake_bedrock_client: Any,
    mock_retrieve_similar: Any,
    memory_checkpointer: Any,
) -> None:
    fake_bedrock_client.complete_json.side_effect = make_analysis_dispatch(flags_per_clause=1)
    out = run_analysis(
        sample_msa_pdf, "t-flags", bedrock=fake_bedrock_client, checkpointer=memory_checkpointer
    )

    assert "__interrupt__" in out
    assert out["status"] == "awaiting_review"
    assert out["redlines"] == []
    assert len(out["flags"]) >= 5

    text_by_id = {c.id: c.text for c in out["contract"].clauses}
    for flag in out["flags"]:
        assert flag.clause_id in text_by_id
        assert flag.verbatim_quote in text_by_id[flag.clause_id]


def test_zero_flags_still_pauses_without_crash(
    sample_msa_pdf: Path,
    fake_bedrock_client: Any,
    mock_retrieve_similar: Any,
    memory_checkpointer: Any,
) -> None:
    fake_bedrock_client.complete_json.side_effect = make_analysis_dispatch(flags_per_clause=0)
    out = run_analysis(
        sample_msa_pdf, "t-zero", bedrock=fake_bedrock_client, checkpointer=memory_checkpointer
    )
    assert "__interrupt__" in out
    assert out["flags"] == []


def test_classify_document_failure_marks_run_failed(
    sample_msa_pdf: Path,
    fake_bedrock_client: Any,
    mock_retrieve_similar: Any,
    memory_checkpointer: Any,
) -> None:
    fake_bedrock_client.complete_json.side_effect = BedrockValidationError("schema mismatch")
    out = run_analysis(
        sample_msa_pdf, "t-fail", bedrock=fake_bedrock_client, checkpointer=memory_checkpointer
    )

    assert "__interrupt__" not in out
    assert out["status"] == "failed"
    assert out["error"] is not None
    assert "classify_document" in out["error"]
    assert out["flags"] == []
