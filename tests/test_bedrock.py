from typing import Any

import pytest
from botocore.exceptions import ClientError
from pydantic import BaseModel
from pytest_mock import MockerFixture

from lexagent.bedrock import BedrockClient, BedrockError, BedrockValidationError
from tests.conftest import make_bedrock_response


class Answer(BaseModel):
    label: str
    confidence: float


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "InvokeModel")


def test_complete_json_returns_validated_instance(bedrock_client: BedrockClient) -> None:
    result, usage = bedrock_client.complete_json("classify this", Answer)
    assert isinstance(result, Answer)
    assert result.label == "important"
    assert result.confidence == 0.9
    assert usage.input_tokens == 1000
    assert usage.output_tokens == 500


def test_cost_estimation(bedrock_client: BedrockClient) -> None:
    _, usage = bedrock_client.complete_json("classify this", Answer)
    assert usage.input_cost_usd == pytest.approx(0.003)
    assert usage.output_cost_usd == pytest.approx(0.0075)
    assert usage.total_cost_usd == pytest.approx(0.0105)


def test_throttling_retries_then_succeeds(bedrock_client: BedrockClient) -> None:
    invoke: Any = bedrock_client._client.invoke_model
    invoke.side_effect = [
        _client_error("ThrottlingException"),
        make_bedrock_response({"label": "minor", "confidence": 0.4}),
    ]
    result, _ = bedrock_client.complete_json("classify this", Answer)
    assert result.label == "minor"
    assert invoke.call_count == 2


def test_validation_failure_retries_once_then_raises(bedrock_client: BedrockClient) -> None:
    invoke: Any = bedrock_client._client.invoke_model
    invoke.side_effect = [
        make_bedrock_response({"label": "only-label"}),
        make_bedrock_response({"label": "still-bad"}),
    ]
    with pytest.raises(BedrockValidationError):
        bedrock_client.complete_json("classify this", Answer)
    assert invoke.call_count == 2


def test_auth_error_does_not_retry(bedrock_client: BedrockClient) -> None:
    invoke: Any = bedrock_client._client.invoke_model
    invoke.side_effect = _client_error("UnrecognizedClientException")
    with pytest.raises(BedrockError):
        bedrock_client.complete_json("classify this", Answer)
    assert invoke.call_count == 1


def test_missing_tool_use_block_raises(mocker: MockerFixture) -> None:
    import io
    import json

    empty = {"body": io.BytesIO(json.dumps({"content": [], "usage": {}}).encode())}
    mock_boto = mocker.MagicMock()
    mock_boto.invoke_model.return_value = empty
    mocker.patch("lexagent.bedrock.boto3.client", return_value=mock_boto)
    with pytest.raises(BedrockValidationError):
        BedrockClient().complete_json("x", Answer)
