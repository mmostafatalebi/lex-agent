"""HTTP error types.

Built on aws-lambda-powertools' ``ServiceError`` hierarchy so the resolver
renders them as JSON with the right status code. The generic 500 handler in
``handler.py`` makes sure no stack trace leaks to clients.
"""

from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    NotFoundError,
    ServiceError,
    UnauthorizedError,
)

__all__ = [
    "BadRequestError",
    "ConflictError",
    "NotFoundError",
    "PayloadTooLargeError",
    "ServiceError",
    "UnauthorizedError",
]


class PayloadTooLargeError(ServiceError):
    """413: the request body exceeds the API Gateway HTTP API limit."""

    def __init__(self, msg: str) -> None:
        super().__init__(413, msg)


class ConflictError(ServiceError):
    """409: the resource is not in a state that allows this operation."""

    def __init__(self, msg: str) -> None:
        super().__init__(409, msg)
