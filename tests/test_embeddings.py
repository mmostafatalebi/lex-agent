import io
import json
from typing import Any

from pytest_mock import MockerFixture

from lexagent.embeddings import EMBEDDING_DIM, EmbeddingsClient


def make_titan_response(dim: int = EMBEDDING_DIM) -> dict[str, Any]:
    payload = {
        "embedding": [i * 0.0001 for i in range(dim)],
        "inputTextTokenCount": 7,
    }
    return {"body": io.BytesIO(json.dumps(payload).encode("utf-8"))}


def _make_client(mocker: MockerFixture) -> tuple[EmbeddingsClient, Any]:
    mock_boto = mocker.MagicMock()
    mocker.patch("lexagent.embeddings.boto3.client", return_value=mock_boto)
    return EmbeddingsClient(), mock_boto


def test_embed_returns_1024_floats(mocker: MockerFixture) -> None:
    client, mock_boto = _make_client(mocker)
    mock_boto.invoke_model.return_value = make_titan_response()
    vector = client.embed("some clause text")
    assert isinstance(vector, list)
    assert len(vector) == 1024
    assert all(isinstance(value, float) for value in vector)


def test_embed_batch_returns_matching_embeddings(mocker: MockerFixture) -> None:
    mocker.patch("lexagent.embeddings.time.sleep")
    client, mock_boto = _make_client(mocker)
    mock_boto.invoke_model.side_effect = [
        make_titan_response(),
        make_titan_response(),
        make_titan_response(),
    ]
    texts = ["clause one", "clause two", "clause three"]
    vectors = client.embed_batch(texts)
    assert len(vectors) == len(texts)
    assert all(len(vector) == 1024 for vector in vectors)
    assert mock_boto.invoke_model.call_count == 3
