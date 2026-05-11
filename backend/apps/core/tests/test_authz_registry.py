"""Unit tests for the authz registry's mutation API.

`test_authz_registry_complete` covers the populated startup state;
this file covers register/get/iter/snapshot mechanics in isolation.
"""

from __future__ import annotations

import pytest

from apps.core.authz.predicates import is_authenticated
from apps.core.authz.types import Activity


def test_register_then_get_returns_rule(empty_registry):
    empty_registry.register(Activity.CATALOG_EDIT, is_authenticated)
    rule = empty_registry.get_rule(Activity.CATALOG_EDIT)
    assert rule is not None
    assert rule.activity is Activity.CATALOG_EDIT
    assert rule.predicates == (is_authenticated,)


def test_get_rule_returns_none_for_unregistered(empty_registry):
    assert empty_registry.get_rule(Activity.CATALOG_EDIT) is None


def test_register_raises_on_duplicate(empty_registry):
    empty_registry.register(Activity.CATALOG_EDIT, is_authenticated)
    with pytest.raises(RuntimeError, match="already registered"):
        empty_registry.register(Activity.CATALOG_EDIT, is_authenticated)


def test_register_raises_on_empty_predicates(empty_registry):
    with pytest.raises(ValueError, match="at least one predicate"):
        empty_registry.register(Activity.CATALOG_EDIT)


def test_iter_rules_returns_all_registered(empty_registry):
    empty_registry.register(Activity.CATALOG_EDIT, is_authenticated)
    empty_registry.register(Activity.CATALOG_CREATE, is_authenticated)
    activities = {r.activity for r in empty_registry.iter_rules()}
    assert activities == {Activity.CATALOG_EDIT, Activity.CATALOG_CREATE}


def test_snapshot_restore_round_trip(empty_registry):
    """Snapshot/restore preserves and reinstates registry state.

    Validates the mechanism the fixture itself depends on. If this
    breaks, every other isolated_registry test breaks silently.
    """
    empty_registry.register(Activity.CATALOG_EDIT, is_authenticated)
    snap = empty_registry._snapshot()

    empty_registry._restore({})
    assert empty_registry.get_rule(Activity.CATALOG_EDIT) is None

    empty_registry._restore(snap)
    assert empty_registry.get_rule(Activity.CATALOG_EDIT) is not None
