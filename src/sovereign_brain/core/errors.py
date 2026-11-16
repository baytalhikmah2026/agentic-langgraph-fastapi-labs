"""Global exception handlers: every failure becomes one clear, consistent error answer."""

import logging

import httpx
import ollama
import openai
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langgraph.errors import GraphRecursionError
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from sovereign_brain.core.request_id import get_request_id
from sovereign_brain.schemas.error import ErrorResponse

logger = logging.getLogger("sovereign_brain.errors")

# The model server is down or the model is missing (Ollama, OpenAI-compatible, raw HTTP)
MODEL_ERRORS = (ConnectionError, ollama.ResponseError, openai.APIConnectionError, httpx.HTTPError)


def error_response(
    status_code: int, error: str, message: str, details=None, headers=None
) -> JSONResponse:
    body = ErrorResponse(
        error=error, message=message, details=details, request_id=get_request_id()
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body), headers=headers)


async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    names = {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
    }
    error = names.get(exc.status_code, "http_error")
    return error_response(exc.status_code, error, str(exc.detail), headers=exc.headers)


async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(part) for part in error["loc"]), "problem": error["msg"]}
        for error in exc.errors()
    ]
    return error_response(422, "invalid_request", "The request data is not valid.", details)


async def model_unavailable(request: Request, exc: Exception) -> JSONResponse:
    logger.error("AI model not available: %r", exc)
    return error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "model_unavailable",
        "The AI model is not available. Please try again later.",
    )


async def database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Database unreachable: %s", exc.orig)
    return error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "database_unavailable",
        "The database is not reachable. Please try again later.",
    )


async def agent_loop_limit(request: Request, exc: GraphRecursionError) -> JSONResponse:
    logger.error("Agent stopped by the recursion limit: %s", exc)
    return error_response(
        status.HTTP_508_LOOP_DETECTED,
        "agent_loop_limit",
        "The agent took too many steps and was stopped.",
    )


async def rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning("Rate limit reached: %s", exc.detail)
    return error_response(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "rate_limited",
        f"Too many model requests. The limit is {exc.detail}; please wait and try again.",
    )


async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unexpected error on %s %s", request.method, request.url.path)
    return error_response(500, "internal_error", "Something went wrong on our side.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    for error in MODEL_ERRORS:
        app.add_exception_handler(error, model_unavailable)
    app.add_exception_handler(OperationalError, database_unavailable)
    app.add_exception_handler(GraphRecursionError, agent_loop_limit)
    app.add_exception_handler(RateLimitExceeded, rate_limited)
    app.add_exception_handler(Exception, unexpected_error)
