"""Structured 403 raised when the policy denies an action.

``PolicyDeniedError`` subclasses :class:`StructuredApiError`, so it routes
through the single handler in ``config/api.py`` and serializes as
``{"detail": {"kind": "policy_denied", "message", "code", "context"}}``
without a per-class handler registration.
"""

from __future__ import annotations

from typing import Any, ClassVar

from apps.core.exceptions import StructuredApiError

from .types import DenialCode, Deny

# Closed-enum mapper: DenialCode → English fallback string. One place.
# The completeness test pins the invariant. These strings are the
# fallback for non-SPA API consumers; the SPA renders code-specific
# copy keyed off `DenialCode` and never reads `message`.
_DENIAL_MESSAGE: dict[DenialCode, str] = {
    DenialCode.AUTH_REQUIRED: "Sign in to continue.",
    DenialCode.ACCOUNT_DEACTIVATED: "Your account is deactivated.",
    DenialCode.ROLE_REQUIRED: "You don't have permission to do that.",
    DenialCode.VERIFICATION_REQUIRED: "Verify your email address to continue.",
    DenialCode.RATE_LIMITED: "You're doing that too often. Try again shortly.",
}


class PolicyDeniedError(StructuredApiError):
    """Raised by ``enforce()`` (and inline ``check()`` callers) on Deny."""

    kind: ClassVar[str] = "policy_denied"
    status: ClassVar[int] = 403

    def __init__(self, decision: Deny) -> None:
        super().__init__(_DENIAL_MESSAGE[decision.code])
        self.decision = decision

    def to_body(self) -> dict[str, Any]:
        return {
            "code": self.decision.code.value,
            "context": dict(self.decision.context),
        }
