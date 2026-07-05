import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
import pytest
from moto import mock_aws
from pytest_mock import MockerFixture

from lexagent.api.analyses import (
    get_analysis,
    get_results,
    start_analysis,
    submit_decisions,
)
from lexagent.api.errors import ConflictError, NotFoundError
from lexagent.api.schemas import StartAnalysisRequest, SubmitDecisionsRequest
from lexagent.models import HumanDecision
from tests.conftest import make_analysis_dispatch

_BUCKET = "lexagent-test-bucket"


@pytest.fixture
def env(
    mocker: MockerFixture,
    mock_retrieve_similar: Any,
    memory_checkpointer: Any,
    sample_msa_pdf: Path,
) -> Iterator[dict[str, Any]]:
    # Build the bedrock mock directly rather than via the fake_bedrock_client
    # fixture, which patches boto3.client globally and would turn the moto-backed
    # S3 client into a no-op mock.
    bedrock = mocker.MagicMock()
    bedrock.complete_json.side_effect = make_analysis_dispatch()

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=_BUCKET)
        mocker.patch("lexagent.api.contracts.settings.s3_bucket", _BUCKET)

        content = sample_msa_pdf.read_bytes()
        contract_id = hashlib.sha256(content).hexdigest()[:16]
        s3.put_object(Bucket=_BUCKET, Key=f"contracts/{contract_id}.pdf", Body=content)
        yield {
            "s3": s3,
            "bedrock": bedrock,
            "checkpointer": memory_checkpointer,
            "contract_id": contract_id,
        }


def _start(env: dict[str, Any]) -> Any:
    return start_analysis(
        StartAnalysisRequest(contract_id=env["contract_id"]),
        env["s3"],
        env["bedrock"],
        env["checkpointer"],
    )


def test_start_analysis_pauses_at_review(env: dict[str, Any]) -> None:
    result = _start(env)
    assert result.status == "awaiting_review"
    assert result.flags
    assert result.redlines is None


def test_get_analysis_returns_same_state(env: dict[str, Any]) -> None:
    started = _start(env)
    fetched = get_analysis(started.thread_id, env["checkpointer"])
    assert fetched.thread_id == started.thread_id
    assert fetched.status == "awaiting_review"
    assert len(fetched.flags or []) == len(started.flags or [])


def test_submit_decisions_completes_with_redlines(env: dict[str, Any]) -> None:
    started = _start(env)
    decisions = [HumanDecision(flag_id=f.id, decision="accept") for f in (started.flags or [])]
    result = submit_decisions(
        started.thread_id,
        SubmitDecisionsRequest(decisions=decisions),
        env["bedrock"],
        env["checkpointer"],
    )
    assert result.status == "complete"
    assert result.redlines


def test_get_results_returns_redlines_when_complete(env: dict[str, Any]) -> None:
    started = _start(env)
    decisions = [HumanDecision(flag_id=f.id, decision="accept") for f in (started.flags or [])]
    submit_decisions(
        started.thread_id,
        SubmitDecisionsRequest(decisions=decisions),
        env["bedrock"],
        env["checkpointer"],
    )
    results = get_results(started.thread_id, env["checkpointer"])
    assert results.status == "complete"
    assert results.redlines


def test_get_results_conflict_when_incomplete(env: dict[str, Any]) -> None:
    started = _start(env)
    with pytest.raises(ConflictError):
        get_results(started.thread_id, env["checkpointer"])


def test_unknown_thread_id_raises_404(env: dict[str, Any]) -> None:
    with pytest.raises(NotFoundError):
        get_analysis("does-not-exist", env["checkpointer"])
    with pytest.raises(NotFoundError):
        get_results("does-not-exist", env["checkpointer"])
    with pytest.raises(NotFoundError):
        submit_decisions(
            "does-not-exist",
            SubmitDecisionsRequest(decisions=[]),
            env["bedrock"],
            env["checkpointer"],
        )


def test_start_analysis_unknown_contract_raises_404(env: dict[str, Any]) -> None:
    with pytest.raises(NotFoundError):
        start_analysis(
            StartAnalysisRequest(contract_id="0000000000000000"),
            env["s3"],
            env["bedrock"],
            env["checkpointer"],
        )
