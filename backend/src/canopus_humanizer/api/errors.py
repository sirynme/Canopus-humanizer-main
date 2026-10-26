"""FastAPI exception handlers for Canopus Humanizer domain errors."""

import logging
import re
from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from canopus_humanizer.engine.errors import (
    ARCHIVE_BOMB_DETECTED,
    CanopusError,
    FormatError,
    INPUT_TOO_LARGE,
    InputError,
    ProtectionError,
    RESOURCE_LIMIT_EXCEEDED,
    ResourceError,
    RULE_NOT_FOUND,
    RulesetError,
    SecurityError,
    ValidationError,
)

logger = logging.getLogger("canopus_humanizer.api")

_PATH_PATTERN = re.compile(r"/(?:home|tmp|usr|var|etc|opt|root)/[^\s'\"]+")


def sanitize_message(message: str) -> str:
    """Sanitizes error messages to prevent exposing internal filesystem paths."""
    if not message:
        return "An internal domain error occurred."
    return _PATH_PATTERN.sub("[REDACTED_PATH]", str(message))


def sanitize_details(details: Any) -> Dict[str, Any]:
    """Sanitizes detail dictionaries to ensure safe client representation."""
    if not isinstance(details, dict):
        return {}
    clean = {}
    for k, v in details.items():
        if isinstance(v, str):
            clean[k] = sanitize_message(v)
        elif isinstance(v, (int, float, bool)):
            clean[k] = v
        elif isinstance(v, list):
            clean[k] = [sanitize_message(i) if isinstance(i, str) else i for i in v]
        elif isinstance(v, dict):
            clean[k] = sanitize_details(v)
    return clean


def format_error_payload(exc: CanopusError) -> Dict[str, Any]:
    """Builds a standardized, safe error envelope."""
    safe_msg = sanitize_message(exc.message)
    return {
        "error": exc.__class__.__name__,
        "code": exc.code or "CANOPUS_ERROR",
        "message": safe_msg,
        "detail": safe_msg,
        "details": sanitize_details(exc.details),
    }


async def input_error_handler(request: Request, exc: InputError) -> JSONResponse:
    """Handler for input validation and normalization errors (e.g. NUL byte)."""
    logger.warning("Input error on %s: [%s] %s", request.url.path, exc.code, exc.message)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=format_error_payload(exc),
    )


async def ruleset_error_handler(request: Request, exc: RulesetError) -> JSONResponse:
    """Handler for ruleset resolution and parsing errors."""
    logger.warning("Ruleset error on %s: [%s] %s", request.url.path, exc.code, exc.message)
    status_code = status.HTTP_404_NOT_FOUND if exc.code == RULE_NOT_FOUND else status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        status_code=status_code,
        content=format_error_payload(exc),
    )


async def resource_error_handler(request: Request, exc: ResourceError) -> JSONResponse:
    """Handler for resource limit boundary violations."""
    logger.warning("Resource error on %s: [%s] %s", request.url.path, exc.code, exc.message)
    if exc.code in (INPUT_TOO_LARGE, RESOURCE_LIMIT_EXCEEDED, ARCHIVE_BOMB_DETECTED):
        status_code = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)
    else:
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse(
        status_code=status_code,
        content=format_error_payload(exc),
    )


async def security_error_handler(request: Request, exc: SecurityError) -> JSONResponse:
    """Handler for security boundary and path traversal violations."""
    logger.error("Security violation on %s: [%s] %s", request.url.path, exc.code, exc.message)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=format_error_payload(exc),
    )


async def protection_error_handler(request: Request, exc: ProtectionError) -> JSONResponse:
    """Handler for protected span corruption or masking failures."""
    logger.warning("Protection error on %s: [%s] %s", request.url.path, exc.code, exc.message)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_payload(exc),
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handler for output validation and semantic drift failures."""
    logger.warning("Validation error on %s: [%s] %s", request.url.path, exc.code, exc.message)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_payload(exc),
    )


async def format_error_handler(request: Request, exc: FormatError) -> JSONResponse:
    """Handler for format adapter and parsing errors."""
    logger.warning("Format error on %s: [%s] %s", request.url.path, exc.code, exc.message)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=format_error_payload(exc),
    )


async def generic_canopus_error_handler(request: Request, exc: CanopusError) -> JSONResponse:
    """Fallback handler for any unspecialized CanopusError subclasses."""
    logger.warning("Canopus error on %s: [%s] %s", request.url.path, exc.code, exc.message)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=format_error_payload(exc),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers all structured domain exception handlers onto a FastAPI application."""
    app.add_exception_handler(InputError, input_error_handler)
    app.add_exception_handler(RulesetError, ruleset_error_handler)
    app.add_exception_handler(ResourceError, resource_error_handler)
    app.add_exception_handler(SecurityError, security_error_handler)
    app.add_exception_handler(ProtectionError, protection_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(FormatError, format_error_handler)
    app.add_exception_handler(CanopusError, generic_canopus_error_handler)
