"""Titan Text Embeddings V2 client.

Produces 1024-dimensional vectors for clause text. Titan does not batch on the
server side, so ``embed_batch`` iterates with a light client-side throttle.
"""

import json
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from lexagent.bedrock import BedrockError, _is_transient
from lexagent.config import settings

EMBEDDING_DIM = 1024

# Light throttle between successive single-text embedding calls.
_INTER_REQUEST_DELAY_SECONDS = 0.02


class EmbeddingsClient:
    def __init__(self) -> None:
        self._client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def embed(self, text: str) -> list[float]:
        """Return a 1024-dim embedding for a single text."""
        body = {"inputText": text}
        try:
            payload = self._invoke(body)
        except ClientError as exc:
            raise BedrockError(str(exc)) from exc

        raw = payload.get("embedding")
        if not isinstance(raw, list):
            raise BedrockError("Embedding response contained no 'embedding' array")
        return [float(value) for value in raw]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for a batch, iterating with a light throttle."""
        results: list[list[float]] = []
        for index, text in enumerate(texts):
            if index and _INTER_REQUEST_DELAY_SECONDS:
                time.sleep(_INTER_REQUEST_DELAY_SECONDS)
            results.append(self.embed(text))
        return results

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(settings.bedrock_max_retries),
        wait=wait_exponential(multiplier=0.2, max=10),
        reraise=True,
    )
    def _invoke(self, body: dict[str, Any]) -> dict[str, Any]:
        response = self._client.invoke_model(
            modelId=settings.bedrock_embedding_model_id,
            body=json.dumps(body),
        )
        payload: dict[str, Any] = json.loads(response["body"].read())
        return payload
