"""End-to-end tests for the `capabilities` field on `/api/auth/me/`.

The capability surface is unit-tested directly in
`apps/core/tests/test_authz_capabilities.py`. This module exercises the
HTTP boundary: the field is present, anonymous gets all-false, and the
verdicts reflect the user's actual flags.
"""

from __future__ import annotations

import pytest

from apps.accounts.test_factories import make_user
from apps.core.authz.types import Activity


@pytest.mark.django_db
class TestMeCapabilities:
    def test_anonymous_capability_map_denies_all(self, client):
        resp = client.get("/api/auth/me/")
        caps = resp.json()["capabilities"]
        assert caps, "expected the capabilities map to be populated"
        assert all(value is False for value in caps.values())

    def test_unverified_user_cannot_edit(self, client):
        user = make_user(email="u@example.test", email_verified=False)
        client.force_login(user)
        caps = client.get("/api/auth/me/").json()["capabilities"]
        assert caps[Activity.CATALOG_EDIT.value] is False
        assert caps[Activity.CITATION_EDIT.value] is False
        assert caps[Activity.MEDIA_EDIT.value] is False

    def test_verified_non_staff_can_edit_but_not_kiosk(self, client):
        user = make_user(email="v@example.test")
        client.force_login(user)
        caps = client.get("/api/auth/me/").json()["capabilities"]
        assert caps[Activity.CATALOG_EDIT.value] is True
        assert caps[Activity.CATALOG_CREATE.value] is True
        assert caps[Activity.CATALOG_DELETE.value] is True
        assert caps[Activity.CITATION_EDIT.value] is True
        assert caps[Activity.MEDIA_EDIT.value] is True
        assert caps[Activity.KIOSK_EDIT.value] is False
        assert caps[Activity.RATE_LIMIT_EXEMPT.value] is False
        assert caps[Activity.DJANGO_ADMIN_ACCESS.value] is False

    def test_verified_staff_unlocks_admin_and_rate_limit_exempt(self, client):
        user = make_user(email="s@example.test", is_staff=True)
        client.force_login(user)
        caps = client.get("/api/auth/me/").json()["capabilities"]
        assert caps[Activity.RATE_LIMIT_EXEMPT.value] is True
        assert caps[Activity.DJANGO_ADMIN_ACCESS.value] is True
        # Kiosk requires superuser, not just staff.
        assert caps[Activity.KIOSK_EDIT.value] is False

    def test_verified_superuser_unlocks_kiosk(self, client):
        user = make_user(email="su@example.test", is_staff=True, is_superuser=True)
        client.force_login(user)
        caps = client.get("/api/auth/me/").json()["capabilities"]
        assert caps[Activity.KIOSK_EDIT.value] is True

    def test_target_aware_activities_are_excluded(self, client):
        user = make_user(email="t@example.test")
        client.force_login(user)
        caps = client.get("/api/auth/me/").json()["capabilities"]
        # `claim.revert` and `changeset.undo` are target-aware; their
        # verdicts come from per-resource hints on each row, not /me/.
        assert Activity.CLAIM_REVERT.value not in caps
        assert Activity.CHANGESET_UNDO.value not in caps
