"""Analysis endpoints: start, status, decisions, results.

Thin wrappers over the existing graph entry points (``run_analysis``,
``resume_analysis``) plus read-only state lookups via the compiled graph.
"""

import tempfile
import uuid
from pathlib import Path
from typing import Any, TypeVar, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel

from lexagent.api.contracts import CONTRACTS_PREFIX
from lexagent.api.errors import ConflictError, NotFoundError
from lexagent.api.schemas import (
    AnalysisStatusResponse,
    ResultsResponse,
    StartAnalysisRequest,
    SubmitDecisionsRequest,
)
from lexagent.bedrock import BedrockClient, TokenUsage
from lexagent.config import settings
from lexagent.graph import build_graph, resume_analysis, run_analysis
from lexagent.models import Flag, Redline

_T = TypeVar("_T", bound=BaseModel)


class _NoopBedrock(BedrockClient):
    """Used only to build the graph for read-only state lookups; never called."""

    def __init__(self) -> None:
        pass

    def complete_json(
        self,
        prompt: str,
        schema: type[_T],
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> tuple[_T, TokenUsage]:
        raise RuntimeError("Bedrock is not available for a read-only operation")


def _require_bucket() -> str:
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET is not configured")
    return settings.s3_bucket


def _find_contract_key(s3_client: Any, contract_id: str) -> str:
    bucket = _require_bucket()
    listing = s3_client.list_objects_v2(Bucket=bucket, Prefix=f"{CONTRACTS_PREFIX}{contract_id}")
    keys = [obj["Key"] for obj in listing.get("Contents", [])]
    if not keys:
        raise NotFoundError(f"No uploaded contract with id {contract_id}")
    return str(keys[0])


def _status_response(thread_id: str, values: dict[str, Any]) -> AnalysisStatusResponse:
    status = values.get("status", "failed")
    if "__interrupt__" in values and status not in {"complete", "failed"}:
        status = "awaiting_review"
    flags = cast("list[Flag] | None", values.get("flags") or None)
    redlines = cast("list[Redline] | None", values.get("redlines") or None)
    return AnalysisStatusResponse(
        thread_id=thread_id,
        status=status,
        flags=flags,
        redlines=redlines,
        error=values.get("error"),
    )


def _read_state(thread_id: str, checkpointer: BaseCheckpointSaver[Any]) -> dict[str, Any]:
    compiled = build_graph(_NoopBedrock(), checkpointer)
    snapshot = compiled.get_state({"configurable": {"thread_id": thread_id}})
    values = snapshot.values
    return values if isinstance(values, dict) else {}


def start_analysis(
    request: StartAnalysisRequest,
    s3_client: Any,
    bedrock: BedrockClient,
    checkpointer: BaseCheckpointSaver[Any],
) -> AnalysisStatusResponse:
    """Download the contract from S3 and run the graph until it pauses or ends."""
    key = _find_contract_key(s3_client, request.contract_id)
    suffix = Path(key).suffix or ".pdf"
    obj = s3_client.get_object(Bucket=_require_bucket(), Key=key)
    content = obj["Body"].read()

    thread_id = uuid.uuid4().hex[:12]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(content)
        tmp_path = Path(handle.name)
    try:
        out = run_analysis(tmp_path, thread_id, bedrock=bedrock, checkpointer=checkpointer)
    finally:
        tmp_path.unlink(missing_ok=True)
    return _status_response(thread_id, out)


def get_analysis(
    thread_id: str, checkpointer: BaseCheckpointSaver[Any]
) -> AnalysisStatusResponse:
    """Fetch the current state of an analysis by thread_id."""
    values = _read_state(thread_id, checkpointer)
    if not values:
        raise NotFoundError(f"No analysis for thread_id {thread_id}")
    return _status_response(thread_id, values)


def submit_decisions(
    thread_id: str,
    request: SubmitDecisionsRequest,
    bedrock: BedrockClient,
    checkpointer: BaseCheckpointSaver[Any],
) -> AnalysisStatusResponse:
    """Resume a paused analysis with human decisions and return the final state."""
    if not _read_state(thread_id, checkpointer):
        raise NotFoundError(f"No analysis for thread_id {thread_id}")
    out = resume_analysis(thread_id, request.decisions, bedrock=bedrock, checkpointer=checkpointer)
    return _status_response(thread_id, out)


def get_results(
    thread_id: str, checkpointer: BaseCheckpointSaver[Any]
) -> ResultsResponse:
    """Fetch the final redlines for a completed analysis."""
    values = _read_state(thread_id, checkpointer)
    if not values:
        raise NotFoundError(f"No analysis for thread_id {thread_id}")
    if values.get("status") != "complete":
        raise ConflictError(f"Analysis {thread_id} is not complete")
    redlines = cast("list[Redline]", values.get("redlines") or [])
    return ResultsResponse(thread_id=thread_id, status="complete", redlines=redlines)
