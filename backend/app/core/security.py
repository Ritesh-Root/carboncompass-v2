"""
Security middleware and utilities.

SecurityHeadersMiddleware adds defence-in-depth HTTP security headers to
every response, conforming to OWASP best practices.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import StringConstraints
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Single source of truth for the device_id format, shared by the Pydantic
# models, the path-parameter validator, and validate_device_id() below.
DEVICE_ID_MIN_LENGTH = 8
DEVICE_ID_MAX_LENGTH = 64
DEVICE_ID_CHARSET = r"^[a-zA-Z0-9_-]+$"

# Reusable annotated type — apply with `device_id: DeviceId` on any model.
DeviceId = Annotated[
    str,
    StringConstraints(
        min_length=DEVICE_ID_MIN_LENGTH,
        max_length=DEVICE_ID_MAX_LENGTH,
        pattern=DEVICE_ID_CHARSET,
    ),
]

_DEVICE_ID_CHARSET_RE = re.compile(DEVICE_ID_CHARSET)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security-related HTTP response headers to every response.

    Headers applied:
      - Content-Security-Policy   — restrict resource origins
      - X-Content-Type-Options    — prevent MIME sniffing
      - X-Frame-Options           — prevent clickjacking
      - X-XSS-Protection          — legacy XSS filter hint
      - Strict-Transport-Security — enforce HTTPS
      - Referrer-Policy           — limit referrer leakage
      - Permissions-Policy        — disable unused browser features
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response: Response = await call_next(request)

        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


def validate_device_id(device_id: str) -> bool:
    """
    Validate that a device_id string matches the expected safe format.

    Args:
        device_id: String to validate.

    Returns:
        True if valid (8–64 chars, alphanumeric + hyphens + underscores).
        False otherwise.
    """
    return (
        DEVICE_ID_MIN_LENGTH <= len(device_id) <= DEVICE_ID_MAX_LENGTH
        and bool(_DEVICE_ID_CHARSET_RE.match(device_id))
    )
