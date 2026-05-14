"""Client IP resolution for pre-auth rate limiting.

Sibling of :mod:`apps.provenance.rate_limits` (per-user). This module
hosts the IP-keyed primitives used by pre-auth flows (signup availability
checks, submit, cancel) where there's no User yet.

For the proxy-chain trust model and the deployment contract behind
``RATE_LIMIT_TRUST_PROXY_HEADERS``, see ``docs/Hosting.md`` § "Client IP
trust".

For now this file only contains :func:`_client_ip` — the rest of the
module (RateLimitExceededError, RateLimitSpec, the signup-flow specs)
arrives with the signup-onboarding branch.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def _client_ip(request: HttpRequest) -> str:
    """Return the client IP used as a rate-limit bucket key.

    Reads ``X-Real-IP`` and never ``X-Forwarded-For`` — XFF parsing has
    no failure mode that's safe under upstream drift. Gated by
    ``RATE_LIMIT_TRUST_PROXY_HEADERS`` (default False); when off, keys
    off ``REMOTE_ADDR``. Both fail closed on drift: degrade to one
    shared bucket, never trust attacker-supplied input.

    Full trust model and deployment contract: ``docs/Hosting.md`` §
    "Client IP trust". Don't add a second forwarded-header reader
    elsewhere; this function is the single sanctioned reader.
    """
    meta = request.META
    if settings.RATE_LIMIT_TRUST_PROXY_HEADERS:
        real_ip = str(meta.get("HTTP_X_REAL_IP") or "").strip()
        if real_ip:
            return real_ip
    return str(meta.get("REMOTE_ADDR") or "unknown")
