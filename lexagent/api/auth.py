"""API key check enforced in Lambda.

HTTP APIs do not support API Gateway usage plans, so the key is validated here
instead. When ``settings.require_api_key`` is False the check is a no-op, which
keeps local development friction-free.
"""

from collections.abc import Mapping

from lexagent.api.errors import UnauthorizedError
from lexagent.config import settings

_HEADER = "x-api-key"


def check_api_key(headers: Mapping[str, str]) -> None:
    """Raise ``UnauthorizedError`` if a required key is missing or wrong."""
    if not settings.require_api_key:
        return
    provided = None
    for name, value in headers.items():
        if name.lower() == _HEADER:
            provided = value
            break
    if not provided or provided != settings.api_key:
        raise UnauthorizedError("Invalid or missing API key")
