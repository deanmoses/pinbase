"""Unit tests for `compute_capability_map`.

The capability map walks the populated registry and returns one verdict
per target-less activity. These tests pin three invariants:

1. Target-aware activities (e.g. `claim.revert`) are excluded.
2. The function is pure — zero database queries.
3. Verdicts match what `check()` would return for each activity.
"""

from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.core.authz.capabilities import compute_capability_map
from apps.core.authz.registry import iter_rules
from apps.core.authz.test_factories import StubPolicyUser
from apps.core.authz.types import Activity


def test_target_aware_activities_are_excluded() -> None:
    user = StubPolicyUser(is_authenticated=True, is_active=True)
    caps = compute_capability_map(user)

    target_aware = {r.activity for r in iter_rules() if r.target_aware}
    assert target_aware, "expected at least one target-aware rule registered"
    assert target_aware.isdisjoint(caps.keys()), (
        f"target-aware activities leaked into the capability map: "
        f"{target_aware & caps.keys()}"
    )


def test_every_target_less_activity_appears_in_the_map() -> None:
    user = StubPolicyUser()
    caps = compute_capability_map(user)
    target_less = {r.activity for r in iter_rules() if not r.target_aware}
    assert caps.keys() == target_less


def test_anonymous_denies_all() -> None:
    anon = StubPolicyUser(
        is_authenticated=False,
        is_active=False,
        is_email_verified=False,
    )
    caps = compute_capability_map(anon)
    assert caps, "expected at least one target-less activity registered"
    assert all(value is False for value in caps.values())


def test_unverified_user_denies_email_gated_activities() -> None:
    user = StubPolicyUser(
        is_authenticated=True,
        is_active=True,
        is_email_verified=False,
    )
    caps = compute_capability_map(user)
    # Editing activities deny on email_verified; RATE_LIMIT_EXEMPT
    # additionally requires `is_staff`, which this user lacks.
    assert caps[Activity.CATALOG_EDIT] is False
    assert caps[Activity.RATE_LIMIT_EXEMPT] is False


def test_unverified_staff_is_not_rate_limit_exempt() -> None:
    """Rate-limit exemption requires email verification.

    Pins the policy intent: an unverified staff account must NOT
    bypass rate limits, even though `is_staff=True` alone would deny
    anonymous correctly. The policy is the security boundary; if an
    unverified staff user ever reaches the rate-limit code path
    (today gated upstream, but the policy can't rely on that), they
    must still consume slots.
    """
    user = StubPolicyUser(
        is_authenticated=True,
        is_active=True,
        is_email_verified=False,
        is_staff=True,
    )
    caps = compute_capability_map(user)
    assert caps[Activity.RATE_LIMIT_EXEMPT] is False


def test_verified_non_staff_allows_editing_denies_staff_only() -> None:
    user = StubPolicyUser(
        is_authenticated=True,
        is_active=True,
        is_email_verified=True,
        is_staff=False,
        is_superuser=False,
    )
    caps = compute_capability_map(user)
    assert caps[Activity.CATALOG_EDIT] is True
    assert caps[Activity.CITATION_EDIT] is True
    assert caps[Activity.MEDIA_EDIT] is True
    assert caps[Activity.KIOSK_EDIT] is False
    assert caps[Activity.RATE_LIMIT_EXEMPT] is False
    assert caps[Activity.DJANGO_ADMIN_ACCESS] is False


def test_verified_staff_allows_staff_activities_but_not_kiosk() -> None:
    user = StubPolicyUser(
        is_authenticated=True,
        is_active=True,
        is_email_verified=True,
        is_staff=True,
        is_superuser=False,
    )
    caps = compute_capability_map(user)
    assert caps[Activity.RATE_LIMIT_EXEMPT] is True
    assert caps[Activity.DJANGO_ADMIN_ACCESS] is True
    assert caps[Activity.KIOSK_EDIT] is False


def test_verified_superuser_allows_kiosk_edit() -> None:
    user = StubPolicyUser(
        is_authenticated=True,
        is_active=True,
        is_email_verified=True,
        is_staff=True,
        is_superuser=True,
    )
    caps = compute_capability_map(user)
    assert caps[Activity.KIOSK_EDIT] is True


@pytest.mark.django_db
def test_compute_capability_map_is_pure() -> None:
    """The walk reads attributes off the user; it must not hit the DB."""
    user = StubPolicyUser(
        is_authenticated=True,
        is_active=True,
        is_email_verified=True,
        is_staff=True,
        is_superuser=True,
    )
    with CaptureQueriesContext(connection) as ctx:
        compute_capability_map(user)
    assert len(ctx) == 0, (
        f"compute_capability_map ran {len(ctx)} queries — the walk must be pure."
    )
