"""Built-in predicates and the `Predicate` callable type.

A predicate is a pure function `(user, target, context) -> Decision`.
Predicates return `Decision` rather than `bool` so each names its own
denial code; the evaluator combines those codes via priority order
when multiple predicates fail.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.db.models import Model

from .types import Allow, Decision, DenialCode, Deny, PolicyContext, PolicyUser

# A predicate is a pure function `(user, target, context) -> Decision`.
# The registry-facing alias intentionally types `target` as `Any` so per-
# rule predicates can declare a narrow Protocol on the parameter
# (`target: ChangeSetPolicyView`) and still satisfy this storage type —
# `Callable` is contravariant in argument types, so a stricter parameter
# would otherwise be incompatible. The narrow Protocol does the real
# enforcement work: at predicate-definition time, mypy checks the body
# against the declared Protocol, so reading any attribute outside the
# Protocol is a static type error caught where it lives. The `Any` here
# is a deliberate registry-level escape hatch, not a hole in the engine's
# type discipline.
Predicate = Callable[[PolicyUser, Any, PolicyContext | None], Decision]


def is_authenticated(
    user: PolicyUser, target: Model | None, context: PolicyContext | None
) -> Decision:
    """Allow when the user has a logged-in session; deny `AUTH_REQUIRED` otherwise."""
    if not user.is_authenticated:
        return Deny(DenialCode.AUTH_REQUIRED)
    return Allow()


def is_active(
    user: PolicyUser, target: Model | None, context: PolicyContext | None
) -> Decision:
    """Allow when `user.is_active` is True; deny `ACCOUNT_DEACTIVATED` otherwise.

    Covers any currently-inactive state (self-deactivation, dormant
    cleanup). Banning is a separate predicate with its own code.
    """
    if not user.is_active:
        return Deny(DenialCode.ACCOUNT_DEACTIVATED)
    return Allow()


def email_verified(
    user: PolicyUser, target: Model | None, context: PolicyContext | None
) -> Decision:
    """Allow when the user's email is verified; deny `VERIFICATION_REQUIRED` otherwise."""
    if not user.email_verified:
        return Deny(DenialCode.VERIFICATION_REQUIRED)
    return Allow()


def is_staff(
    user: PolicyUser, target: Model | None, context: PolicyContext | None
) -> Decision:
    """Allow when `user.is_staff` is True; deny `ROLE_REQUIRED` with `required_role=staff`.

    Independent from `is_superuser` — the policy does not treat
    superusers as implicit staff.
    """
    if not user.is_staff:
        return Deny(DenialCode.ROLE_REQUIRED, {"required_role": "staff"})
    return Allow()


def is_superuser(
    user: PolicyUser, target: Model | None, context: PolicyContext | None
) -> Decision:
    """Allow when `user.is_superuser` is True; deny `ROLE_REQUIRED` with `required_role=superuser`.

    Independent from `is_staff` — see `is_staff` for the orthogonality
    contract.
    """
    if not user.is_superuser:
        return Deny(DenialCode.ROLE_REQUIRED, {"required_role": "superuser"})
    return Allow()
