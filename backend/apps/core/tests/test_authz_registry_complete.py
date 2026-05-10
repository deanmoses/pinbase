"""Asserts every Activity has a registered rule at startup.

This test deliberately does NOT use the `isolated_registry` fixture.
It reads the real, app-`ready()`-populated registry and would pass
trivially against an empty one.

A new `Activity` enum member with no per-app rule registration is what
this catches: the runtime would `LookupError` instead of returning a
permission decision, which is correct but only useful if someone hits
the route. This test makes that misconfiguration a CI failure.
"""

from __future__ import annotations

import pytest

from apps.core.authz.evaluator import check
from apps.core.authz.registry import get_rule
from apps.core.authz.test_factories import StubPolicyUser
from apps.core.authz.types import Activity, DenialCode, Deny


@pytest.mark.parametrize("activity", list(Activity))
def test_every_activity_has_a_registered_rule(activity: Activity) -> None:
    rule = get_rule(activity)
    assert rule is not None, (
        f"Activity {activity!r} has no registered rule. Add a "
        f"`register({activity.name}, ...)` call to the relevant app's "
        f"`authz.py`, and ensure that `apps.py: ready()` imports the "
        f"module."
    )
    assert rule.predicates, (
        f"Activity {activity!r} registered with no predicates — that "
        f"would auto-allow every caller. Register at least "
        f"`is_authenticated, is_active`."
    )


@pytest.mark.parametrize("activity", list(Activity))
def test_every_activity_requires_email_verified(activity: Activity) -> None:
    """An authenticated, active, unverified user must be denied with
    VERIFICATION_REQUIRED on every launch activity.

    A future activity that forgets the `email_verified` predicate would
    auto-allow unverified users — this test pins that invariant. Different
    failure mode than the rule-presence test above, so kept as a separate
    function rather than a parametrize expansion.
    """
    user = StubPolicyUser(
        is_authenticated=True, is_active=True, is_email_verified=False
    )
    decision = check(user, activity)
    assert isinstance(decision, Deny), (
        f"Activity {activity!r} allowed an unverified user — missing "
        f"`email_verified` predicate in the rule registration."
    )
    assert decision.code is DenialCode.VERIFICATION_REQUIRED, (
        f"Activity {activity!r} denied an unverified user with code "
        f"{decision.code!r}, expected VERIFICATION_REQUIRED."
    )
