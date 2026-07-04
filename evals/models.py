"""Pydantic schemas for the evaluation harness."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from lexagent.models import DocumentType, Flag, Severity


class ExpectedFlag(BaseModel):
    """Ground-truth flag we expect the analysis to identify."""

    model_config = ConfigDict(frozen=True)

    clause_hint: str  # substring of the clause's heading or number
    expected_severity: Severity
    risk_category: str  # controlled vocabulary; see evals.RISK_CATEGORIES
    verbatim_hint: str  # substring the detected quote should contain


class FixtureCase(BaseModel):
    """One hand-labelled contract case."""

    model_config = ConfigDict(frozen=True)

    name: str  # e.g. "msa_problematic"
    contract_path: Path
    expected_document_type: DocumentType
    expected_flags: list[ExpectedFlag]


class FlagMatch(BaseModel):
    """Result of matching a detected flag to an expected flag (or none)."""

    model_config = ConfigDict(frozen=True)

    expected: ExpectedFlag | None
    detected: Flag | None
    is_match: bool
    match_reasoning: str


class RetrievalEvalResult(BaseModel):
    """Retrieval quality scores for one fixture."""

    model_config = ConfigDict(frozen=True)

    fixture_name: str
    context_precision: float
    context_recall: float


class AnalysisEvalResult(BaseModel):
    """Scores for the analysis pipeline on one fixture."""

    model_config = ConfigDict(frozen=True)

    fixture_name: str
    precision: float  # detected ∩ expected / detected
    recall: float  # detected ∩ expected / expected
    f1: float
    document_type_correct: bool
    matches: list[FlagMatch]
    hallucination_rate: float  # detected flags with no supporting clause content


class FixtureReport(BaseModel):
    """Everything scored for a single fixture, ready for the report."""

    model_config = ConfigDict(frozen=True)

    analysis: AnalysisEvalResult
    retrieval: RetrievalEvalResult
    detected_count: int
    expected_count: int
    matched_count: int
