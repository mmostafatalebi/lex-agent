"""Contract upload handler: base64 body to S3, content-addressed."""

import base64
import binascii
import hashlib
from pathlib import Path
from typing import Any

from lexagent.api.errors import BadRequestError, PayloadTooLargeError
from lexagent.api.schemas import UploadContractRequest, UploadContractResponse
from lexagent.config import settings

CONTRACTS_PREFIX = "contracts/"
MAX_CONTENT_BYTES = 6 * 1024 * 1024  # API Gateway HTTP API payload limit
_ALLOWED_SUFFIXES = {".pdf", ".docx"}


def upload_contract(request: UploadContractRequest, s3_client: Any) -> UploadContractResponse:
    """Upload a contract PDF or DOCX to S3. Returns a contract_id and the S3 key."""
    suffix = Path(request.filename).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise BadRequestError(f"Unsupported file type: {request.filename}")

    try:
        content = base64.b64decode(request.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BadRequestError("content_base64 is not valid base64") from exc

    if not content:
        raise BadRequestError("content_base64 decoded to an empty file")
    if len(content) > MAX_CONTENT_BYTES:
        raise PayloadTooLargeError("Contract exceeds the 6MB upload limit")

    bucket = _require_bucket()
    contract_id = hashlib.sha256(content).hexdigest()[:16]
    s3_key = f"{CONTRACTS_PREFIX}{contract_id}{suffix}"
    s3_client.put_object(Bucket=bucket, Key=s3_key, Body=content)

    return UploadContractResponse(contract_id=contract_id, s3_key=s3_key)


def _require_bucket() -> str:
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET is not configured")
    return settings.s3_bucket
