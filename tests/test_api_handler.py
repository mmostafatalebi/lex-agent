import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import boto3
from langgraph.checkpoint.memory import MemorySaver
from moto import mock_aws
from pytest_mock import MockerFixture

from lexagent.api import handler
from tests.conftest import make_analysis_dispatch, make_http_event

_BUCKET = "lexagent-handler-bucket"


class _Ctx:
    function_name = "test"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    aws_request_id = "req-1"


# LambdaContext is a Protocol; a plain stand-in is fine at runtime.
CTX: Any = _Ctx()


def test_unknown_route_returns_404_json() -> None:
    response = handler.lambda_handler(make_http_event("GET", "/does-not-exist"), CTX)
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "message" in body


def test_non_json_body_returns_400_json() -> None:
    response = handler.lambda_handler(
        make_http_event("POST", "/contracts", body="this is not json"), CTX
    )
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "message" in body


def test_unhandled_exception_returns_500_without_leak(mocker: MockerFixture) -> None:
    def _boom() -> Any:
        raise RuntimeError("secret internal detail")

    mocker.patch.object(handler, "_s3_client", _boom)
    event = make_http_event(
        "POST", "/contracts", body=json.dumps({"filename": "x.pdf", "content_base64": "aGk="})
    )
    response = handler.lambda_handler(event, CTX)
    assert response["statusCode"] == 500
    assert "secret internal detail" not in response["body"]
    assert "Traceback" not in response["body"]


def test_full_flow_through_handler(
    mocker: MockerFixture, mock_retrieve_similar: Any, sample_msa_pdf: Path
) -> None:
    bedrock = mocker.MagicMock()
    bedrock.complete_json.side_effect = make_analysis_dispatch()
    checkpointer = MemorySaver()

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=_BUCKET)
        mocker.patch("lexagent.api.contracts.settings.s3_bucket", _BUCKET)
        mocker.patch.object(handler, "_s3_client", lambda: s3)
        mocker.patch.object(handler, "_bedrock", lambda: bedrock)
        mocker.patch.object(handler, "_checkpointer", lambda: checkpointer)

        content = sample_msa_pdf.read_bytes()
        upload_body = json.dumps(
            {"filename": "sample.pdf", "content_base64": base64.b64encode(content).decode()}
        )
        upload = handler.lambda_handler(
            make_http_event("POST", "/contracts", body=upload_body), CTX
        )
        assert upload["statusCode"] == 200
        contract_id = json.loads(upload["body"])["contract_id"]
        assert contract_id == hashlib.sha256(content).hexdigest()[:16]

        start = handler.lambda_handler(
            make_http_event("POST", "/analyses", body=json.dumps({"contract_id": contract_id})),
            CTX,
        )
        assert start["statusCode"] == 200
        started = json.loads(start["body"])
        thread_id = started["thread_id"]
        assert started["status"] == "awaiting_review"

        status = handler.lambda_handler(
            make_http_event("GET", f"/analyses/{thread_id}"), CTX
        )
        assert status["statusCode"] == 200

        decisions = [{"flag_id": f["id"], "decision": "accept"} for f in started["flags"]]
        submitted = handler.lambda_handler(
            make_http_event(
                "POST",
                f"/analyses/{thread_id}/decisions",
                body=json.dumps({"decisions": decisions}),
            ),
            CTX,
        )
        assert submitted["statusCode"] == 200
        assert json.loads(submitted["body"])["status"] == "complete"

        results = handler.lambda_handler(
            make_http_event("GET", f"/analyses/{thread_id}/results"), CTX
        )
        assert results["statusCode"] == 200
        assert json.loads(results["body"])["redlines"]


def test_migrations_handler_runs_alembic(mocker: MockerFixture) -> None:
    upgrade = mocker.patch("alembic.command.upgrade")
    mocker.patch("alembic.config.Config")
    result = handler.migrations_handler({}, CTX)
    assert result == {"status": "ok"}
    upgrade.assert_called_once()


def test_seed_handler_runs_script(mocker: MockerFixture) -> None:
    run_path = mocker.patch("runpy.run_path")
    result = handler.seed_handler({}, CTX)
    assert result == {"status": "ok"}
    run_path.assert_called_once()
