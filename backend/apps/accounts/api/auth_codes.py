"""Error codes for the WorkOS callback view.

`AuthErrorCode` is the typed discriminator the callback redirects with
(`/auth/error?reason=<code>`) and the frontend `/auth/error` page narrows on.
`LoginRefusedError` carries a code alongside its human-readable message so
the catch site in `auth_callback` can map to the URL parameter without
inspecting `str(exc)`.

This module is distinct from `apps/accounts/auth_errors.py` (Session 2's
`StructuredApiError` subclasses for the Ninja signup endpoints): that's a
JSON envelope mechanism for typed API errors, this is a view-layer redirect
mechanism for the OAuth callback. Different layers, different transports.
"""

from __future__ import annotations

from typing import Literal

AuthErrorCode = Literal[
    "email_unverified",
    "account_conflict",
    "account_disabled",
    "state_invalid",
    "code_exchange_failed",
]


class LoginRefusedError(Exception):
    """Raised when an inbound WorkOS login may not be honored.

    Surfaced as a redirect to /auth/error?reason=<code> in auth_callback.
    The message is preserved for logging (`log.warning("Login refused: %s", exc)`)
    so ops can correlate refusal reasons without scraping query strings.
    """

    def __init__(self, code: AuthErrorCode, message: str) -> None:
        super().__init__(message)
        self.code: AuthErrorCode = code
