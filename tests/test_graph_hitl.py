from pathlib import Path
from typing import Any, Literal

from lexagent.checkpoint import get_checkpointer
from lexagent.graph import resume_analysis, run_analysis
from lexagent.models import HumanDecision
from tests.conftest import make_analysis_dispatch


def _decisions(flags: list[Any], decision: Literal["accept", "reject"]) -> list[HumanDecision]:
    return [HumanDecision(flag_id=flag.id, decision=decision) for flag in flags]


def test_pause_then_resume_produces_redlines(
    sample_msa_pdf: Path,
    fake_bedrock_client: Any,
    mock_retrieve_similar: Any,
    memory_checkpointer: Any,
) -> None:
    fake_bedrock_client.complete_json.side_effect = make_analysis_dispatch()
    out = run_analysis(
        sample_msa_pdf, "t-resume", bedrock=fake_bedrock_client, checkpointer=memory_checkpointer
    )
    assert "__interrupt__" in out
    assert out["redlines"] == []

    flags = out["flags"]
    accepted = flags[:3]
    decisions = _decisions(accepted, "accept") + _decisions(flags[3:], "reject")
    final = resume_analysis(
        "t-resume", decisions, bedrock=fake_bedrock_client, checkpointer=memory_checkpointer
    )

    assert final["status"] == "complete"
    assert len(final["redlines"]) == len(accepted)
    text_by_id = {c.id: c.text for c in final["contract"].clauses}
    for redline in final["redlines"]:
        assert redline.original_text in text_by_id[redline.clause_id]


def test_all_rejects_produce_no_redlines(
    sample_msa_pdf: Path,
    fake_bedrock_client: Any,
    mock_retrieve_similar: Any,
    memory_checkpointer: Any,
) -> None:
    fake_bedrock_client.complete_json.side_effect = make_analysis_dispatch()
    out = run_analysis(
        sample_msa_pdf, "t-reject", bedrock=fake_bedrock_client, checkpointer=memory_checkpointer
    )
    decisions = _decisions(out["flags"], "reject")
    final = resume_analysis(
        "t-reject", decisions, bedrock=fake_bedrock_client, checkpointer=memory_checkpointer
    )
    assert final["status"] == "complete"
    assert final["redlines"] == []


def test_persistence_across_reopened_checkpointer(
    sample_msa_pdf: Path,
    fake_bedrock_client: Any,
    mock_retrieve_similar: Any,
    tmp_path: Path,
) -> None:
    checkpoint_file = tmp_path / "checkpoints.db"
    fake_bedrock_client.complete_json.side_effect = make_analysis_dispatch()

    # First process: run until interrupt, then drop the checkpointer.
    saver_a = get_checkpointer(str(checkpoint_file))
    out = run_analysis(
        sample_msa_pdf, "t-persist", bedrock=fake_bedrock_client, checkpointer=saver_a
    )
    assert "__interrupt__" in out
    accepted = out["flags"][:2]
    decisions = _decisions(accepted, "accept") + _decisions(out["flags"][2:], "reject")
    del saver_a

    # Second process: reopen the same file and resume.
    saver_b = get_checkpointer(str(checkpoint_file))
    final = resume_analysis(
        "t-persist", decisions, bedrock=fake_bedrock_client, checkpointer=saver_b
    )
    assert final["status"] == "complete"
    assert len(final["redlines"]) == len(accepted)
