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
    changeset: ChangeSetPolicyView,
    context: PolicyContext | None,
) -> Decision:
    """Allow when the caller authored ``changeset``; else ``OWNER_REQUIRED``.

    The defensive ``changeset is None`` guard lives in the evaluator
    (``check()``), not here — any target-aware rule called without a
    target raises ``TypeError`` before reaching its predicates.
    """
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
