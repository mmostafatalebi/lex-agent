"""Lambda entry point.

All routes are served by one function; aws-lambda-powertools handles routing.
AWS clients and the checkpointer are cached at module scope so warm invocations
skip re-initialisation.
"""

import functools
import json
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, Response, content_types
from aws_lambda_powertools.utilities.typing import LambdaContext
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import ValidationError

from lexagent.api.analyses import get_analysis, get_results, start_analysis, submit_decisions
from lexagent.api.auth import check_api_key
from lexagent.api.contracts import upload_contract
from lexagent.api.errors import BadRequestError
from lexagent.api.schemas import (
    StartAnalysisRequest,
    SubmitDecisionsRequest,
    UploadContractRequest,
)
from lexagent.bedrock import BedrockClient
from lexagent.checkpoint import get_checkpointer
from lexagent.config import settings

logger = Logger()
app = APIGatewayHttpResolver()


@functools.lru_cache(maxsize=1)
def _s3_client() -> Any:
    return boto3.client("s3", region_name=settings.aws_region)


@functools.lru_cache(maxsize=1)
def _bedrock() -> BedrockClient:
    return BedrockClient()


@functools.lru_cache(maxsize=1)
def _checkpointer() -> BaseCheckpointSaver[Any]:
    return get_checkpointer()


def _json_body() -> dict[str, Any]:
    try:
        body = app.current_event.json_body
    except Exception as exc:
        raise BadRequestError("Request body must be valid JSON") from exc
    if not isinstance(body, dict):
        raise BadRequestError("Request body must be a JSON object")
    return body


@app.post("/contracts")
def _upload_contract() -> dict[str, Any]:
    check_api_key(app.current_event.headers)
    request = UploadContractRequest.model_validate(_json_body())
    return upload_contract(request, _s3_client()).model_dump()


@app.post("/analyses")
def _start_analysis() -> dict[str, Any]:
    check_api_key(app.current_event.headers)
    request = StartAnalysisRequest.model_validate(_json_body())
    return start_analysis(request, _s3_client(), _bedrock(), _checkpointer()).model_dump()


@app.get("/analyses/<thread_id>")
def _get_analysis(thread_id: str) -> dict[str, Any]:
    check_api_key(app.current_event.headers)
    return get_analysis(thread_id, _checkpointer()).model_dump()


@app.post("/analyses/<thread_id>/decisions")
def _submit_decisions(thread_id: str) -> dict[str, Any]:
    check_api_key(app.current_event.headers)
    request = SubmitDecisionsRequest.model_validate(_json_body())
    return submit_decisions(thread_id, request, _bedrock(), _checkpointer()).model_dump()


@app.get("/analyses/<thread_id>/results")
def _get_results(thread_id: str) -> dict[str, Any]:
    check_api_key(app.current_event.headers)
    return get_results(thread_id, _checkpointer()).model_dump()


@app.exception_handler(ValidationError)  # type: ignore[untyped-decorator]
def _on_validation_error(exc: ValidationError) -> Response[str]:
    return Response(
        status_code=400,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps({"message": "Invalid request payload"}),
    )


def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    # powertools handles ServiceError (4xx) natively; anything else that escapes
    # becomes a generic 500 so no internal detail leaks to the client.
    try:
        return app.resolve(event, context)
    except Exception:
        logger.exception("Unhandled error")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": content_types.APPLICATION_JSON},
            "body": json.dumps({"message": "Internal server error"}),
            "isBase64Encoded": False,
        }


def migrations_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, str]:
    """Run ``alembic upgrade head``. Invoked by a CDK custom resource on deploy."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("/var/task/alembic.ini")
    cfg.set_main_option("script_location", "/var/task/migrations")
    command.upgrade(cfg, "head")
    return {"status": "ok"}


def seed_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, str]:
    """Seed the taxonomy. Invoked by a CDK custom resource on deploy."""
    import runpy

    runpy.run_path("/var/task/scripts/seed_taxonomy.py", run_name="__main__")
    return {"status": "ok"}
