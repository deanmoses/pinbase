"""Unit tests for the ``check_policy_activities`` system check.

The check walks every ninja Schema subclass and validates each
``policy_activities`` declaration against the registry. These tests
exercise its individual error branches with synthetic Schemas.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar, Protocol

from django.core.checks import CheckMessage
from ninja import Schema

from apps.core.authz.checks import check_policy_activities
from apps.core.authz.predicates import is_authenticated
from apps.core.authz.types import Activity


class _NotAFieldProtocol(Protocol):
    @property
    def nonexistent_attr(self) -> int: ...


def _ids_for(messages: Iterable[CheckMessage], schema: type) -> set[str]:
    """Error IDs whose ``obj`` is the given schema. Tests share the
    Schema subclass space, so scoping by ``obj`` keeps assertions from
    interfering with one another.
    """
    return {m.id for m in messages if m.obj is schema and m.id is not None}


def test_clean_no_schemas_no_errors(empty_registry):
    """A target-aware activity with no schema declaring it raises nothing."""
    empty_registry.register(
        Activity.CLAIM_REVERT,
        is_authenticated,
        target_aware=True,
    )
    # Filter to errors not attributable to any test's synthetic schema —
    # only the one we care about: nothing for Activity.CLAIM_REVERT
    # itself, since no schema declares it.
    errors = check_policy_activities(None)
    # No assertions on global error count; only that adding the rule
    # doesn't itself surface an error.
    assert all(m.id != "authz.E103" or "claim.revert" not in m.msg for m in errors)


def test_non_list_policy_activities_errors(empty_registry):
    class BadSchema(Schema):
        policy_activities: ClassVar[str] = "not a list"

    errors = check_policy_activities(None)
    assert "authz.E101" in _ids_for(errors, BadSchema)


def test_non_activity_member_errors(empty_registry):
    class WrongMemberSchema(Schema):
        policy_activities: ClassVar[list[str]] = ["not.an.activity"]

    errors = check_policy_activities(None)
    assert "authz.E102" in _ids_for(errors, WrongMemberSchema)


def test_unregistered_activity_errors(empty_registry):
    class GhostSchema(Schema):
        policy_activities: ClassVar[list[Activity]] = [Activity.CHANGESET_UNDO]

    errors = check_policy_activities(None)
    assert "authz.E103" in _ids_for(errors, GhostSchema)


def test_target_less_activity_on_row_schema_errors(empty_registry):
    empty_registry.register(
        Activity.CATALOG_EDIT,
        is_authenticated,
    )

    class TargetlessSchema(Schema):
        policy_activities: ClassVar[list[Activity]] = [Activity.CATALOG_EDIT]

    errors = check_policy_activities(None)
    assert "authz.E104" in _ids_for(errors, TargetlessSchema)


def test_target_aware_without_protocol_is_ok(empty_registry):
    """Wire-slot reservation case: target-aware but no Protocol.

    ``claim.revert`` ships in this state today. The check allows it —
    nothing structural to validate against — and the schema author
    explicitly listing the activity stays the safeguard.
    """
    empty_registry.register(
        Activity.CLAIM_REVERT,
        is_authenticated,
        target_aware=True,
    )

    class FineSchema(Schema):
        policy_activities: ClassVar[list[Activity]] = [Activity.CLAIM_REVERT]

    errors = check_policy_activities(None)
    assert _ids_for(errors, FineSchema) == set()


def test_protocol_attr_missing_on_model_errors(empty_registry):
    """Protocol declares an attribute the schema's declared model doesn't expose."""
    from django.contrib.auth import get_user_model

    user_model = get_user_model()

    empty_registry.register(
        Activity.CHANGESET_UNDO,
        is_authenticated,
        target_aware=True,
        target=_NotAFieldProtocol,
    )

    class UserBackedSchema(Schema):
        policy_activities: ClassVar[list[Activity]] = [Activity.CHANGESET_UNDO]
        policy_target_model: ClassVar[type] = user_model

    errors = check_policy_activities(None)
    assert "authz.E105" in _ids_for(errors, UserBackedSchema)


def test_missing_policy_target_model_errors(empty_registry):
    """``policy_activities`` without ``policy_target_model`` raises E106.

    Plain ninja ``Schema`` subclasses don't expose their model. Without
    an explicit declaration, the structural check has nothing to
    validate against — so requiring the declaration keeps the system
    check honest. The explicit ``policy_target_model`` is the schema
    author's commitment that the structural check has run.
    """
    empty_registry.register(
        Activity.CHANGESET_UNDO,
        is_authenticated,
        target_aware=True,
        target=_NotAFieldProtocol,
    )

    class NoModelSchema(Schema):
        policy_activities: ClassVar[list[Activity]] = [Activity.CHANGESET_UNDO]

    errors = check_policy_activities(None)
    assert "authz.E106" in _ids_for(errors, NoModelSchema)


def test_wire_slot_only_activity_does_not_require_model(empty_registry):
    """Activities without a target Protocol (wire-slot reservation)
    don't need ``policy_target_model`` — there's nothing to validate."""
    empty_registry.register(
        Activity.CLAIM_REVERT,
        is_authenticated,
        target_aware=True,
    )

    class WireSlotOnlySchema(Schema):
        policy_activities: ClassVar[list[Activity]] = [Activity.CLAIM_REVERT]

    errors = check_policy_activities(None)
    assert "authz.E106" not in _ids_for(errors, WireSlotOnlySchema)
