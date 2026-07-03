import logging
from pathlib import Path
from typing import Any

import pytest

from lexagent.models import (
    Clause,
    ClauseType,
    Contract,
    DocumentType,
    Flag,
    GraphState,
    Severity,
)
from lexagent.nodes.analyze_clause import AnalysisResult, FlagDraft, analyze_clause
from lexagent.nodes.classify_clauses import (
    ClauseClassificationBatch,
    ClauseClassificationEntry,
    classify_clauses,
)
from lexagent.nodes.classify_document import DocumentClassification, classify_document
from lexagent.nodes.ingest import IngestError, ingest
from lexagent.nodes.rank import rank
from tests.conftest import make_usage


def _clause(cid: str, text: str, ctype: ClauseType | None = None) -> Clause:
    return Clause(id=cid, text=text, clause_type=ctype, char_start=0, char_end=len(text))


def _contract(clauses: list[Clause], doc: DocumentType = DocumentType.MSA) -> Contract:
    raw = "\n\n".join(c.text for c in clauses)
    return Contract(id="c1", filename="c.pdf", document_type=doc, raw_text=raw, clauses=clauses)


# --- ingest ---


def test_ingest_populates_contract(sample_msa_pdf: Path) -> None:
    state = ingest(GraphState(), sample_msa_pdf)
    assert state.contract is not None
    assert len(state.contract.clauses) >= 6
    assert state.status == "analyzing"


def test_ingest_unsupported_extension_raises(tmp_path: Path) -> None:
    bad = tmp_path / "contract.txt"
    bad.write_text("not a contract format")
    with pytest.raises(IngestError):
        ingest(GraphState(), bad)


# --- classify_document ---


def test_classify_document_sets_type(fake_bedrock_client: Any) -> None:
    state = GraphState(contract=_contract([_clause("clause_001", "Some agreement text.")]))
    fake_bedrock_client.complete_json.return_value = (
        DocumentClassification(document_type=DocumentType.MSA, reasoning="looks like an MSA"),
        make_usage(),
    )
    result = classify_document(state, fake_bedrock_client)
    assert result.contract is not None
    assert result.contract.document_type is DocumentType.MSA
    assert result.total_cost_usd > 0


# --- classify_clauses ---


def test_classify_clauses_sets_every_type(fake_bedrock_client: Any) -> None:
    clauses = [_clause("clause_001", "IP text"), _clause("clause_002", "Payment text")]
    state = GraphState(contract=_contract(clauses))
    fake_bedrock_client.complete_json.return_value = (
        ClauseClassificationBatch(
            classifications=[
                ClauseClassificationEntry(
                    clause_id="clause_001", clause_type=ClauseType.IP_ASSIGNMENT
                ),
                ClauseClassificationEntry(
                    clause_id="clause_002", clause_type=ClauseType.PAYMENT_TERMS
                ),
            ]
        ),
        make_usage(),
    )
    result = classify_clauses(state, fake_bedrock_client)
    assert result.contract is not None
    types = {c.id: c.clause_type for c in result.contract.clauses}
    assert types["clause_001"] is ClauseType.IP_ASSIGNMENT
    assert types["clause_002"] is ClauseType.PAYMENT_TERMS


def test_classify_clauses_fills_missing_with_other(fake_bedrock_client: Any) -> None:
    clauses = [_clause("clause_001", "IP text"), _clause("clause_002", "Unlabeled text")]
    state = GraphState(contract=_contract(clauses))
    fake_bedrock_client.complete_json.return_value = (
        ClauseClassificationBatch(
            classifications=[
                ClauseClassificationEntry(
                    clause_id="clause_001", clause_type=ClauseType.IP_ASSIGNMENT
                ),
            ]
        ),
        make_usage(),
    )
    result = classify_clauses(state, fake_bedrock_client)
    assert result.contract is not None
    types = {c.id: c.clause_type for c in result.contract.clauses}
    assert types["clause_001"] is ClauseType.IP_ASSIGNMENT
    assert types["clause_002"] is ClauseType.OTHER


# --- analyze_clause ---


def test_analyze_clause_produces_flags(
    fake_bedrock_client: Any, mock_retrieve_similar: Any
) -> None:
    text = "Contractor shall be liable for any and all damages without limitation."
    clause = _clause("clause_006", text, ClauseType.LIABILITY)
    state = GraphState(contract=_contract([clause]))
    fake_bedrock_client.complete_json.return_value = (
        AnalysisResult(
            flags=[
                FlagDraft(
                    risk_description="Unlimited liability",
                    severity=Severity.DEALBREAKER,
                    verbatim_quote="liable for any and all damages without limitation",
                    reasoning="No cap exposes the contractor.",
                )
            ]
        ),
        make_usage(),
    )
    result = analyze_clause(state, fake_bedrock_client)
    assert len(result.flags) == 1
    flag = result.flags[0]
    assert flag.clause_id == "clause_006"
    assert flag.id == "flag_clause_006_001"
    assert flag.verbatim_quote in text


def test_analyze_clause_skips_other_clauses(
    fake_bedrock_client: Any, mock_retrieve_similar: Any
) -> None:
    clause = _clause("clause_010", "General boilerplate.", ClauseType.OTHER)
    state = GraphState(contract=_contract([clause]))
    result = analyze_clause(state, fake_bedrock_client)
    assert result.flags == []
    fake_bedrock_client.complete_json.assert_not_called()


def test_analyze_clause_verbatim_gate_drops_and_warns(
    fake_bedrock_client: Any, mock_retrieve_similar: Any, caplog: pytest.LogCaptureFixture
) -> None:
    text = "Client may terminate at any time for any reason."
    clause = _clause("clause_005", text, ClauseType.TERMINATION)
    state = GraphState(contract=_contract([clause]))
    bad_flag = FlagDraft(
        risk_description="Paraphrased risk",
        severity=Severity.IMPORTANT,
        verbatim_quote="the client can end the contract whenever it likes",
        reasoning="Not a real substring.",
    )
    fake_bedrock_client.complete_json.side_effect = [
        (AnalysisResult(flags=[bad_flag]), make_usage()),
        (AnalysisResult(flags=[bad_flag]), make_usage()),
    ]
    with caplog.at_level(logging.WARNING, logger="lexagent.nodes.analyze_clause"):
        result = analyze_clause(state, fake_bedrock_client)
    assert result.flags == []
    assert fake_bedrock_client.complete_json.call_count == 2
    assert any("Dropping flag" in record.message for record in caplog.records)


# --- rank ---


def test_rank_orders_by_severity_then_clause_order() -> None:
    clauses = [
        _clause("clause_001", "a"),
        _clause("clause_002", "b"),
        _clause("clause_003", "c"),
    ]
    contract = _contract(clauses)
    flags = [
        Flag(
            id="f1",
            clause_id="clause_003",
            risk_description="minor issue",
            severity=Severity.MINOR,
            verbatim_quote="c",
            reasoning="r",
        ),
        Flag(
            id="f2",
            clause_id="clause_002",
            risk_description="dealbreaker issue",
            severity=Severity.DEALBREAKER,
            verbatim_quote="b",
            reasoning="r",
        ),
        Flag(
            id="f3",
            clause_id="clause_001",
            risk_description="important issue",
            severity=Severity.IMPORTANT,
            verbatim_quote="a",
            reasoning="r",
        ),
        Flag(
            id="f4",
            clause_id="clause_003",
            risk_description="dealbreaker further down the document",
            severity=Severity.DEALBREAKER,
            verbatim_quote="c",
            reasoning="r",
        ),
    ]
    state = GraphState(contract=contract, flags=flags)
    result = rank(state)
    assert [f.id for f in result.flags] == ["f2", "f4", "f3", "f1"]
    assert result.status == "awaiting_review"
