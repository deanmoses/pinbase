"""Test fixtures shared across `apps.core` tests."""

from __future__ import annotations

from collections.abc import Iterator
from types import ModuleType

import pytest

from apps.core.authz import registry as _registry


@pytest.fixture
def isolated_registry() -> Iterator[ModuleType]:
    """Snapshot the authz registry; restore on teardown.

    Tests that *mutate* the registry (register fake activities, assert
    duplicate-raises, etc.) MUST use this fixture so their writes don't
    leak across tests and silently destroy the startup-populated state
    that `test_authz_registry_complete` depends on.

    Tests that only *read* the registry — `test_authz_registry_complete`
    is the canonical example — do NOT use this fixture; they rely on the
    real, app-`ready()`-populated state.
    """
    snapshot = _registry._snapshot()
    try:
        yield _registry
    finally:
        _registry._restore(snapshot)


@pytest.fixture
def empty_registry(isolated_registry: ModuleType) -> ModuleType:
    """Like `isolated_registry`, but starts empty.

    Useful for tests that re-register a launch activity (e.g.
    `Activity.CATALOG_EDIT`) under different predicates — the
    startup-populated registry would already hold that key and raise.
    """
    isolated_registry._restore({})
    return isolated_registry
