"""Small Vortex HTTP helpers used by routers and services."""

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from vortex.constants.http import HTTPStatusCodes
from vortex.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    VortexException,
)
from vortex.response import send_response

HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_CONFLICT = 409


def send_success_response(
    data: Any = None,
    status_code: int = HTTPStatusCodes.SUCCESS.value,
) -> JSONResponse:
    """Return Vortex's standard success envelope after encoding app models."""
    return send_response(data=jsonable_encoder(data), status_code=status_code)


def bad_request(error: str) -> BadRequestException:
    return BadRequestException(error)


def conflict(error: str) -> VortexException:
    return VortexException(error, status_code=HTTP_CONFLICT)


def forbidden(error: str) -> ForbiddenException:
    return ForbiddenException(error)


def internal_server_error(error: str) -> VortexException:
    return VortexException(
        error, status_code=HTTPStatusCodes.INTERNAL_SERVER_ERROR.value
    )


def not_found(error: str) -> NotFoundException:
    return NotFoundException(error)


def service_unavailable(error: str) -> VortexException:
    return VortexException(error, status_code=HTTPStatusCodes.SERVICE_UNAVAILABLE.value)


def unauthorized(error: str) -> VortexException:
    return VortexException(error, status_code=HTTPStatusCodes.UNAUTHORIZED.value)
