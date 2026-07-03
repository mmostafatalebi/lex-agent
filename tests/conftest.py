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


def make_usage(input_tokens: int = 100, output_tokens: int = 50) -> Any:
    """Build a TokenUsage with cost derived from the client's price constants."""
    from lexagent.bedrock import (
        INPUT_COST_PER_MTOKEN_USD,
        OUTPUT_COST_PER_MTOKEN_USD,
        TokenUsage,
    )

    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_usd=input_tokens / 1_000_000 * INPUT_COST_PER_MTOKEN_USD,
        output_cost_usd=output_tokens / 1_000_000 * OUTPUT_COST_PER_MTOKEN_USD,
    )


@pytest.fixture
def fake_bedrock_client(mocker: MockerFixture) -> Any:
    """A BedrockClient whose ``complete_json`` is a mock for tests to configure."""
    from lexagent.bedrock import BedrockClient

    mocker.patch("lexagent.bedrock.boto3.client", return_value=mocker.MagicMock())
    client = BedrockClient()
    mocker.patch.object(client, "complete_json")
    return client


@pytest.fixture
def mock_retrieve_similar(mocker: MockerFixture) -> Any:
    """Patch retrieval at the analyze-node boundary with canned taxonomy examples."""
    from lexagent.models import ClauseType
    from lexagent.retrieve import RetrievedExample

    examples = [
        RetrievedExample(
            clause_type=ClauseType.LIABILITY,
            text="Each party's liability is capped at the fees paid in the prior 12 months.",
            is_risky=False,
            notes="Balanced mutual cap.",
            similarity=0.88,
        ),
        RetrievedExample(
            clause_type=ClauseType.LIABILITY,
            text="Contractor shall be liable for any and all damages without limitation.",
            is_risky=True,
            notes="Uncapped one-sided liability.",
            similarity=0.81,
        ),
    ]
    return mocker.patch(
        "lexagent.nodes.analyze_clause.retrieve_similar", return_value=examples
    )
