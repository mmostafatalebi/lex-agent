"""HTTP request/response schemas.

Kept separate from the domain models so the wire format can evolve without
touching the graph. Domain models (``Flag``, ``Redline``, ``HumanDecision``) are
embedded directly where the API returns them verbatim.
"""

from typing import Literal

from pydantic import BaseModel

from lexagent.models import Flag, HumanDecision, Redline


class UploadContractRequest(BaseModel):
    filename: str
    content_base64: str  # base64-encoded PDF/DOCX bytes


class UploadContractResponse(BaseModel):
    contract_id: str
    s3_key: str


class StartAnalysisRequest(BaseModel):
    contract_id: str


class AnalysisStatusResponse(BaseModel):
    thread_id: str
    status: Literal["awaiting_review", "drafting", "complete", "failed"]
    flags: list[Flag] | None = None
    redlines: list[Redline] | None = None
    error: str | None = None


class SubmitDecisionsRequest(BaseModel):
    decisions: list[HumanDecision]


class ResultsResponse(BaseModel):
    thread_id: str
    status: Literal["complete"]
    redlines: list[Redline]
