import base64
import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
import pytest
from moto import mock_aws
from pytest_mock import MockerFixture

from lexagent.api.contracts import MAX_CONTENT_BYTES, upload_contract
from lexagent.api.errors import BadRequestError, PayloadTooLargeError
from lexagent.api.schemas import UploadContractRequest

_BUCKET = "lexagent-test-bucket"


@pytest.fixture
def s3_client(mocker: MockerFixture) -> Iterator[Any]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        mocker.patch("lexagent.api.contracts.settings.s3_bucket", _BUCKET)
        yield client


def _request_from_bytes(filename: str, content: bytes) -> UploadContractRequest:
    return UploadContractRequest(
        filename=filename, content_base64=base64.b64encode(content).decode("ascii")
    )


def test_upload_stores_object_and_returns_content_address(
    s3_client: Any, sample_msa_pdf: Path
) -> None:
    content = sample_msa_pdf.read_bytes()
    request = _request_from_bytes("sample.pdf", content)
    result = upload_contract(request, s3_client)

    assert result.contract_id == hashlib.sha256(content).hexdigest()[:16]
    assert result.s3_key == f"contracts/{result.contract_id}.pdf"
    stored = s3_client.get_object(Bucket=_BUCKET, Key=result.s3_key)["Body"].read()
    assert stored == content


def test_same_content_is_idempotent(s3_client: Any) -> None:
    request = _request_from_bytes("a.pdf", b"%PDF-1.4 identical bytes")
    first = upload_contract(request, s3_client)
    second = upload_contract(_request_from_bytes("b.pdf", b"%PDF-1.4 identical bytes"), s3_client)
    assert first.contract_id == second.contract_id


def test_invalid_base64_raises(s3_client: Any) -> None:
    request = UploadContractRequest(filename="a.pdf", content_base64="not valid base64!!")
    with pytest.raises(BadRequestError):
        upload_contract(request, s3_client)


def test_unsupported_extension_raises(s3_client: Any) -> None:
    request = _request_from_bytes("a.txt", b"hello")
    with pytest.raises(BadRequestError):
        upload_contract(request, s3_client)


def test_oversized_content_raises_413(s3_client: Any) -> None:
    request = _request_from_bytes("big.pdf", b"x" * (MAX_CONTENT_BYTES + 1))
    with pytest.raises(PayloadTooLargeError):
        upload_contract(request, s3_client)
