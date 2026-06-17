"""
Rate limiting configuration using slowapi (Starlette-compatible wrapper for limits).

The limiter keys on the client's real IP address. Behind a proxy/load balancer
(e.g. Cloud Run, which is the deployment target), the direct peer address is the
platform's front end, not the user — so we read the left-most hop of
``X-Forwarded-For`` and only fall back to the peer address when the header is
absent. Limits are defined as constants so routes can reference them by name.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip_key(request: Request) -> str:
    """Return the originating client IP for rate-limiting.

    Cloud Run sets ``X-Forwarded-For`` with the original client as the first
    entry. We trust that single, platform-managed proxy hop; if the header is
    missing (e.g. local dev, direct connection) we use the peer address.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return get_remote_address(request)


# Shared limiter instance — must be attached to app.state.limiter in main.py
limiter = Limiter(key_func=client_ip_key)

# Per-route rate limit strings (requests/minute)
CALCULATE_LIMIT = "30/minute"
INSIGHTS_LIMIT = "10/minute"
ENTRIES_LIMIT = "20/minute"
