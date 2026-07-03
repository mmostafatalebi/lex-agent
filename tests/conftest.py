import io
import json
from pathlib import Path
from typing import Any

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_msa_pdf(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "sample_msa.pdf"
    if not path.exists():
        pytest.skip("sample_msa.pdf not generated; run scripts/build_fixtures.py")
    return path


@pytest.fixture
def sample_msa_docx(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "sample_msa.docx"
    if not path.exists():
        pytest.skip("sample_msa.docx not generated; run scripts/build_fixtures.py")
    return path


def make_bedrock_response(
    tool_input: dict[str, Any],
    input_tokens: int = 1000,
    output_tokens: int = 500,
) -> dict[str, Any]:
    """Build an invoke_model response with a single tool_use block."""
    payload = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_test",
                "name": "emit_structured_output",
                "input": tool_input,
            }
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
    return {"body": io.BytesIO(json.dumps(payload).encode("utf-8"))}


@pytest.fixture
def mocked_bedrock_response() -> dict[str, Any]:
    return make_bedrock_response({"label": "important", "confidence": 0.9})


@pytest.fixture
def bedrock_client(mocker: MockerFixture, mocked_bedrock_response: dict[str, Any]) -> Any:
    """A BedrockClient wired to a mocked boto3 bedrock-runtime client.

    The underlying mock is reachable as ``client._client`` so tests can override
    ``invoke_model`` with custom return values or side effects.
    """
    from lexagent.bedrock import BedrockClient

    mock_boto = mocker.MagicMock()
    mock_boto.invoke_model.return_value = mocked_bedrock_response
    mocker.patch("lexagent.bedrock.boto3.client", return_value=mock_boto)
    return BedrockClient()
