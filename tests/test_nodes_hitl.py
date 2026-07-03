import logging
from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pytest_mock import MockerFixture

from lexagent.models import (
    Clause,
    ClauseType,
    Contract,
    DocumentType,
    Flag,
    GraphState,
    HumanDecision,
    Redline,
    RedlineDraft,
    Severity,
)
from lexagent.nodes.draft_redlines import draft_redlines
from lexagent.nodes.human_review import human_review
from lexagent.nodes.validate_redlines import validate_redlines
from tests.conftest import make_usage


def _flag(fid: str, cid: str = "clause_001", quote: str = "q") -> Flag:
    return Flag(
        id=fid,
        clause_id=cid,
        risk_description="r",
        severity=Severity.IMPORTANT,
        verbatim_quote=quote,
        reasoning="x",
    )


def _clause(cid: str, text: str) -> Clause:
    return Clause(
        id=cid, text=text, clause_type=ClauseType.LIABILITY, char_start=0, char_end=len(text)
    )


def _contract(clauses: list[Clause]) -> Contract:
    raw = "\n\n".join(c.text for c in clauses)
    return Contract(
        id="c1",
        filename="c.pdf",
        document_type=DocumentType.MSA,
        raw_text=raw,
        clauses=clauses,
    )


# --- human_review ---


def test_human_review_interrupts_with_flag_payload() -> None:
    flag = _flag("flag_a")

    def node(state: GraphState) -> dict[str, Any]:
        result = human_review(state)
        return {"human_decisions": result.human_decisions, "status": result.status}

    graph = StateGraph(GraphState)
    graph.add_node("hr", node)
    graph.set_entry_point("hr")
    graph.add_edge("hr", END)
    compiled = graph.compile(checkpointer=MemorySaver())

    out = compiled.invoke(GraphState(flags=[flag]), config={"configurable": {"thread_id": "x"}})
    assert "__interrupt__" in out
    payload = out["__interrupt__"][0].value
    assert [entry["id"] for entry in payload["flags"]] == ["flag_a"]


def test_human_review_applies_decisions(mocker: MockerFixture) -> None:
    flag = _flag("flag_a")
    mocker.patch(
        "lexagent.nodes.human_review.interrupt",
        return_value=[{"flag_id": "flag_a", "decision": "accept", "comment": None}],
    )
    result = human_review(GraphState(flags=[flag]))
    assert result.status == "drafting"
    assert len(result.human_decisions) == 1
    assert result.human_decisions[0].flag_id == "flag_a"
    assert result.human_decisions[0].decision == "accept"


def test_human_review_rejects_unknown_flag_id(mocker: MockerFixture) -> None:
    flag = _flag("flag_a")
    mocker.patch(
        "lexagent.nodes.human_review.interrupt",
        return_value=[{"flag_id": "flag_unknown", "decision": "accept"}],
    )
    with pytest.raises(ValueError, match="Unknown flag_id"):
        human_review(GraphState(flags=[flag]))


# --- draft_redlines ---


def test_draft_redlines_one_per_accepted(fake_bedrock_client: Any) -> None:
    text = "Contractor shall be liable for any and all damages without limitation."
    clause = _clause("clause_006", text)
    flags = [
        _flag("flag_006_001", "clause_006", "liable for any and all damages"),
        _flag("flag_006_002", "clause_006", "without limitation"),
    ]
    decisions = [
        HumanDecision(flag_id="flag_006_001", decision="accept"),
        HumanDecision(flag_id="flag_006_002", decision="reject"),
    ]
    state = GraphState(contract=_contract([clause]), flags=flags, human_decisions=decisions)
    fake_bedrock_client.complete_json.return_value = (
        RedlineDraft(
            original_text="liable for any and all damages",
            revised_text="liable only up to the fees paid",
            justification="Caps the exposure.",
        ),
        make_usage(),
    )
    result = draft_redlines(state, fake_bedrock_client)
    assert len(result.redlines) == 1
    assert result.redlines[0].flag_id == "flag_006_001"
    assert result.redlines[0].original_text in text
    assert fake_bedrock_client.complete_json.call_count == 1


def test_draft_redlines_retry_succeeds(fake_bedrock_client: Any) -> None:
    text = "Client may terminate at any time for any reason."
    clause = _clause("clause_005", text)
    flags = [_flag("flag_005_001", "clause_005", "terminate at any time")]
    decisions = [HumanDecision(flag_id="flag_005_001", decision="accept")]
    state = GraphState(contract=_contract([clause]), flags=flags, human_decisions=decisions)
    fake_bedrock_client.complete_json.side_effect = [
        (
            RedlineDraft(
                original_text="paraphrase not in the clause",
                revised_text="x",
                justification="j",
            ),
            make_usage(),
        ),
        (
            RedlineDraft(
                original_text="terminate at any time",
                revised_text="terminate on thirty days' notice",
                justification="Adds notice.",
            ),
            make_usage(),
        ),
    ]
    result = draft_redlines(state, fake_bedrock_client)
    assert len(result.redlines) == 1
    assert result.redlines[0].original_text == "terminate at any time"
    assert fake_bedrock_client.complete_json.call_count == 2


def test_draft_redlines_drops_and_warns(
    fake_bedrock_client: Any, caplog: pytest.LogCaptureFixture
) -> None:
    text = "Client may terminate at any time for any reason."
    clause = _clause("clause_005", text)
    flags = [_flag("flag_005_001", "clause_005", "terminate")]
    decisions = [HumanDecision(flag_id="flag_005_001", decision="accept")]
    state = GraphState(contract=_contract([clause]), flags=flags, human_decisions=decisions)
    bad = (
        RedlineDraft(original_text="never present here", revised_text="x", justification="j"),
        make_usage(),
    )
    fake_bedrock_client.complete_json.side_effect = [bad, bad]
    with caplog.at_level(logging.WARNING, logger="lexagent.nodes.draft_redlines"):
        result = draft_redlines(state, fake_bedrock_client)
    assert result.redlines == []
    assert fake_bedrock_client.complete_json.call_count == 2
    assert any("Dropping redline" in record.message for record in caplog.records)


# --- validate_redlines ---


def test_validate_redlines_drops_non_substring(caplog: pytest.LogCaptureFixture) -> None:
    text = "Client shall pay each invoice within thirty days."
    clause = _clause("clause_002", text)
    good = Redline(
        id="r_good",
        clause_id="clause_002",
        flag_id="f1",
        original_text="within thirty days",
        revised_text="within fifteen days",
        justification="j",
    )
    bad = Redline(
        id="r_bad",
        clause_id="clause_002",
        flag_id="f2",
        original_text="a passage that never appears",
        revised_text="x",
        justification="j",
    )
    state = GraphState(contract=_contract([clause]), redlines=[good, bad])
    with caplog.at_level(logging.WARNING, logger="lexagent.nodes.validate_redlines"):
        result = validate_redlines(state)
    assert [r.id for r in result.redlines] == ["r_good"]
    assert any("Dropping redline" in record.message for record in caplog.records)


def test_validate_redlines_keeps_smart_quote_match() -> None:
    # The clause uses fullwidth digits; the redline quotes ascii digits. NFKC
    # folds the fullwidth forms so the substring check still matches.
    text = "Payment is due within ３０ days of receipt."  # noqa: RUF001
    clause = _clause("clause_002", text)
    redline = Redline(
        id="r1",
        clause_id="clause_002",
        flag_id="f1",
        original_text="within 30 days",  # ascii digits
        revised_text="within 15 days",
        justification="j",
    )
    state = GraphState(contract=_contract([clause]), redlines=[redline])
    result = validate_redlines(state)
    assert [r.id for r in result.redlines] == ["r1"]


def test_validate_redlines_sets_status_complete() -> None:
    clause = _clause("clause_001", "Some clause text.")
    result = validate_redlines(GraphState(contract=_contract([clause]), redlines=[]))
    assert result.status == "complete"
