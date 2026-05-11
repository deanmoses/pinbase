"""Provenance activity rules."""

from __future__ import annotations

from typing import Protocol

from apps.core.authz.predicates import email_verified, is_active, is_authenticated
from apps.core.authz.registry import register
from apps.core.authz.types import (
    Activity,
    Allow,
    Decision,
    DenialCode,
    Deny,
    PolicyContext,
    PolicyUser,
)


class ChangeSetPolicyView(Protocol):
    """Attribute surface ``is_changeset_author`` may read off a ChangeSet.

    Declared as read-only ``@property`` so mypy treats the predicate as
    type-checked against this narrow shape — any reach for an attribute
    outside this Protocol (e.g. ``changeset.user.username``) is a static
    error at predicate-definition time, which is what keeps the no-I/O
    discipline honest.
    """

    @property
    def id(self) -> int: ...

    @property
    def user_id(self) -> int | None: ...


def is_changeset_author(
    user: PolicyUser,
    changeset: ChangeSetPolicyView | None,
    context: PolicyContext | None,
) -> Decision:
    """Allow when the caller authored ``changeset``; else ``OWNER_REQUIRED``.

    A target-aware predicate called with ``changeset=None`` is a
    programming error (the route forgot to pass ``target=``), not a
    permission decision. Surface it as a ``TypeError`` so it becomes a
    500 — same shape as the evaluator's ``LookupError`` on a missing
    rule. Returning a Deny here would mask the bug as a misleading 403.
    """
    if changeset is None:
        raise TypeError("is_changeset_author requires a target")
    if changeset.user_id != user.id:
        return Deny(DenialCode.OWNER_REQUIRED)
    return Allow()


register(
    Activity.CLAIM_REVERT,
    is_authenticated,
    is_active,
    email_verified,
    target_aware=True,
)
register(
    Activity.CHANGESET_UNDO,
    is_authenticated,
    is_active,
    email_verified,
    is_changeset_author,
    target_aware=True,
    target=ChangeSetPolicyView,
)
