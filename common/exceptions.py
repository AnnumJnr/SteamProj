"""
Custom exception handler.
Wraps DRF's default exception handling to produce a consistent
JSON error response shape across all endpoints.

Response shape:
{
    "error": {
        "code": "string",
        "message": "string",
        "details": {} | [] | null
    }
}
"""

import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Called by DRF whenever an exception is raised in a view.
    Normalizes all error responses to a consistent shape.
    """

    # Let DRF handle the exception first to get a standard response
    response = exception_handler(exc, context)

    if response is not None:
        # Reformat DRF's default error structure into our standard shape
        error_detail = response.data

        # Determine a human-readable message from the error detail
        if isinstance(error_detail, dict):
            message = _extract_message_from_dict(error_detail)
        elif isinstance(error_detail, list):
            message = str(error_detail[0]) if error_detail else "An error occurred."
        else:
            message = str(error_detail)

        response.data = {
            "error": {
                "code": _get_error_code(response.status_code),
                "message": message,
                "details": error_detail,
            }
        }

    else:
        # Unhandled exception — log it and return a generic 500
        logger.error(
            "Unhandled exception in view: %s",
            str(exc),
            exc_info=True,
            extra={"view": str(context.get("view"))},
        )
        response = Response(
            {
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": None,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _extract_message_from_dict(error_dict: dict) -> str:
    """Pull the first meaningful error message from a DRF error dict."""
    for key, value in error_dict.items():
        if key == "detail":
            return str(value)
        if isinstance(value, list) and value:
            return f"{key}: {value[0]}"
        if isinstance(value, str):
            return f"{key}: {value}"
    return "Validation failed."


def _get_error_code(status_code: int) -> str:
    """Map HTTP status codes to readable error code strings."""
    codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "unprocessable_entity",
        429: "too_many_requests",
        500: "internal_server_error",
    }
    return codes.get(status_code, "error")