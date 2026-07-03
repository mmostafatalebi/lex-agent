"""Durable Pydantic schemas for the whole LexAgent system.

Every model that represents extracted or parsed data is frozen so downstream
nodes cannot mutate it in place. ``GraphState`` is the single mutable model:
LangGraph nodes replace its fields rather than mutating them.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    MSA = "msa"
    NDA = "nda"
    SOW = "sow"
    SERVICE_AGREEMENT = "service_agreement"
    OTHER = "other"


class ClauseType(StrEnum):
    IP_ASSIGNMENT = "ip_assignment"
    PAYMENT_TERMS = "payment_terms"
    TERMINATION = "termination"
    LIABILITY = "liability"
    CONFIDENTIALITY = "confidentiality"
    INDEMNIFICATION = "indemnification"
    NON_COMPETE = "non_compete"
    DISPUTE_RESOLUTION = "dispute_resolution"
    SCOPE_OF_WORK = "scope_of_work"
    OTHER = "other"


class Severity(StrEnum):
    DEALBREAKER = "dealbreaker"
    IMPORTANT = "important"
    MINOR = "minor"


class Clause(BaseModel):
    """A single clause parsed from a contract. Offsets are into Contract.raw_text."""

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "clause_001"
    section_number: str | None = None  # e.g. "3.2" or "Article 4"
    heading: str | None = None  # e.g. "Payment Terms"
    text: str
    clause_type: ClauseType | None = None
    char_start: int
    char_end: int


class Contract(BaseModel):
    """A parsed contract with clauses and character-offset tracking."""

    model_config = ConfigDict(frozen=True)

    id: str
    filename: str
    document_type: DocumentType = DocumentType.OTHER
    raw_text: str
    clauses: list[Clause] = Field(default_factory=list)


class Flag(BaseModel):
    """A risk or missing-protection issue identified in a clause."""

    model_config = ConfigDict(frozen=True)

    id: str
    clause_id: str
    risk_description: str
    severity: Severity
    verbatim_quote: str  # must be a literal substring of Contract.raw_text
    reasoning: str
    suggested_redline: str | None = None


class HumanDecision(BaseModel):
    """The human reviewer's decision on a single flag."""

    model_config = ConfigDict(frozen=True)

    flag_id: str
    decision: Literal["accept", "reject"]
    comment: str | None = None


class Redline(BaseModel):
    """A drafted revision to a specific clause, produced only for accepted flags."""

    model_config = ConfigDict(frozen=True)

    id: str
    clause_id: str
    flag_id: str  # the accepted flag that triggered this redline
    original_text: str  # verbatim from the source clause
    revised_text: str
    justification: str


class GraphState(BaseModel):
    """The mutable state carried through the LangGraph state machine.

    This is the only mutable Pydantic model in the system. Nodes replace fields
    rather than mutating them in place.
    """

    contract: Contract | None = None
    flags: list[Flag] = Field(default_factory=list)
    human_decisions: list[HumanDecision] = Field(default_factory=list)
    redlines: list[Redline] = Field(default_factory=list)
    status: Literal[
        "pending",
        "ingesting",
        "analyzing",
        "awaiting_review",
        "drafting",
        "complete",
        "failed",
    ] = "pending"
    error: str | None = None
    total_cost_usd: float = 0.0
