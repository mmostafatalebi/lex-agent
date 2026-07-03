"""Typed AWS Bedrock client for Claude with structured output.

Structured output is enforced through Anthropic's tool-use interface: a single
tool whose ``input_schema`` is the caller's Pydantic schema, with ``tool_choice``
forcing the model to invoke it. Responses are validated against that schema, with
one stricter-prompt retry before failing closed.
"""

import json
from typing import Any, TypeVar

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from lexagent.config import settings

INPUT_COST_PER_MTOKEN_USD = 3.0
OUTPUT_COST_PER_MTOKEN_USD = 15.0

TRANSIENT_ERROR_CODES = frozenset(
    {"ThrottlingException", "ServiceUnavailableException", "ModelStreamErrorException"}
)

_ANTHROPIC_VERSION = "bedrock-2023-05-31"
_TOOL_NAME = "emit_structured_output"
_STRICTER_HINT = (
    "Your previous response did not match the schema. "
    "Return only a tool_use call with valid arguments."
)

T = TypeVar("T", bound=BaseModel)


class BedrockError(Exception):
    """Bedrock returned an unrecoverable error."""


class BedrockValidationError(BedrockError):
    """Bedrock returned content that failed schema validation."""


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    input_cost_usd: float
    output_cost_usd: float

    @property
    def total_cost_usd(self) -> float:
        return self.input_cost_usd + self.output_cost_usd


def _is_transient(exc: BaseException) -> bool:
    """True for throttling / transient service errors that are worth retrying."""
    if not isinstance(exc, ClientError):
        return False
    code = exc.response.get("Error", {}).get("Code")
    return code in TRANSIENT_ERROR_CODES


def _usage_from_counts(input_tokens: int, output_tokens: int) -> TokenUsage:
    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_usd=input_tokens / 1_000_000 * INPUT_COST_PER_MTOKEN_USD,
        output_cost_usd=output_tokens / 1_000_000 * OUTPUT_COST_PER_MTOKEN_USD,
    )


class BedrockClient:
    def __init__(self) -> None:
        self._client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def complete_json(
        self,
        prompt: str,
        schema: type[T],
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> tuple[T, TokenUsage]:
        """Return a validated instance of ``schema`` plus usage/cost."""
        tool = self._build_tool(schema)
        system_prompt = system
        last_error: ValidationError | None = None

        for _ in range(2):
            body = self._build_body(prompt, tool, system_prompt, temperature, max_tokens)
            try:
                payload = self._invoke(body)
            except ClientError as exc:
                raise BedrockError(str(exc)) from exc

            args, usage = self._parse_tool_use(payload)
            try:
                return schema.model_validate(args), usage
            except ValidationError as exc:
                last_error = exc
                system_prompt = (
                    _STRICTER_HINT if system is None else f"{system}\n\n{_STRICTER_HINT}"
                )

        raise BedrockValidationError(f"Response failed schema validation: {last_error}")

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(settings.bedrock_max_retries),
        wait=wait_exponential(multiplier=0.2, max=10),
        reraise=True,
    )
    def _invoke(self, body: dict[str, Any]) -> dict[str, Any]:
        response = self._client.invoke_model(
            modelId=settings.bedrock_model_id,
            body=json.dumps(body),
        )
        payload: dict[str, Any] = json.loads(response["body"].read())
        return payload

    @staticmethod
    def _build_tool(schema: type[BaseModel]) -> dict[str, Any]:
        return {
            "name": _TOOL_NAME,
            "description": "Emit the structured result as this tool's arguments.",
            "input_schema": schema.model_json_schema(),
        }

    @staticmethod
    def _build_body(
        prompt: str,
        tool: dict[str, Any],
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "anthropic_version": _ANTHROPIC_VERSION,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": _TOOL_NAME},
        }
        if system is not None:
            body["system"] = system
        return body

    @staticmethod
    def _parse_tool_use(payload: dict[str, Any]) -> tuple[Any, TokenUsage]:
        content = payload.get("content", [])
        tool_input: Any = None
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_input = block.get("input")
                break
        if tool_input is None:
            raise BedrockValidationError("Response contained no tool_use block")

        usage_block = payload.get("usage", {})
        usage = _usage_from_counts(
            int(usage_block.get("input_tokens", 0)),
            int(usage_block.get("output_tokens", 0)),
        )
        return tool_input, usage
