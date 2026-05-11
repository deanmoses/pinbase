"""Unit tests for the ``target=`` kwarg on ``register()``."""

from __future__ import annotations

from typing import Protocol

import pytest

from apps.core.authz.predicates import is_authenticated
from apps.core.authz.types import Activity


class _DummyTargetView(Protocol):
    @property
    def id(self) -> int: ...
    @property
    def user_id(self) -> int: ...


def test_register_accepts_target_protocol(empty_registry):
    empty_registry.register(
        Activity.CHANGESET_UNDO,
        is_authenticated,
        target_aware=True,
        target=_DummyTargetView,
    )
    rule = empty_registry.get_rule(Activity.CHANGESET_UNDO)
    assert rule is not None
    assert rule.target is _DummyTargetView
    assert rule.target_aware is True


def test_register_target_without_target_aware_raises(empty_registry):
    with pytest.raises(ValueError, match="target_aware=False"):
        empty_registry.register(
            Activity.CATALOG_EDIT,
            is_authenticated,
            target=_DummyTargetView,
        )


def test_register_target_aware_without_target_is_allowed(empty_registry):
    """Wire-slot reservation: ``claim.revert`` is target-aware but its
    current rule reads no target attributes, so no Protocol is declared.
    """
    empty_registry.register(
        Activity.CLAIM_REVERT,
        is_authenticated,
        target_aware=True,
    )
    rule = empty_registry.get_rule(Activity.CLAIM_REVERT)
    assert rule is not None
    assert rule.target is None
    assert rule.target_aware is True
