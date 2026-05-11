"""Asserts every app that owns activities imported its `authz` module.

Catches the "forgot `from . import authz` in `apps.py: ready()`" bug
class. Without this test, the failure mode is "new Activity enum
member silently has no rule" — which `test_authz_registry_complete`
also catches, but only after the symptom appears. This test catches
the cause: a missing `ready()` import.
"""

from __future__ import annotations

import sys

import pytest

# Modules that register at least one Activity. Update if a new app
# starts registering rules. Core uses `core/authz/` as the engine
# package, so its rules live in `core/authz/rules.py` instead of the
# usual `<app>/authz.py`.
_AUTHZ_RULE_MODULES = (
    "apps.core.authz.rules",
    "apps.catalog.authz",
    "apps.provenance.authz",
    "apps.citation.authz",
    "apps.media.authz",
    "apps.kiosk.authz",
)


@pytest.mark.parametrize("authz_module", _AUTHZ_RULE_MODULES)
def test_app_authz_module_is_imported(authz_module: str) -> None:
    assert authz_module in sys.modules, (
        f"{authz_module} not imported. Ensure the owning app's "
        f"`apps.py: ready()` imports it so registration runs at "
        f"startup."
    )
