"""Tests for accounts admin (User add/change forms)."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User


@pytest.fixture
def admin_client(superuser: User) -> Client:
    c = Client()
    c.force_login(superuser)
    return c


@pytest.mark.django_db
class TestUserAdminAdd:
    def test_admin_add_derives_username(self, admin_client):
        """The admin add view bypasses UserManager, so save_model must derive."""
        url = reverse("admin:accounts_user_add")
        resp = admin_client.post(
            url,
            {
                "email": "newuser@example.com",
                "password1": "complexpass123",  # pragma: allowlist secret
                "password2": "complexpass123",  # pragma: allowlist secret
            },
        )
        # Django admin redirects on success; a 200 means form errors.
        assert resp.status_code == 302, getattr(resp, "context", None)

        user = User.objects.get(email="newuser@example.com")
        assert user.username == "newuser"

    def test_admin_add_two_users_same_local_part(self, admin_client):
        """Sequential admin adds with the same local-part don't collide."""
        url = reverse("admin:accounts_user_add")
        for email in ("alice@example.com", "alice@other.com"):
            resp = admin_client.post(
                url,
                {
                    "email": email,
                    "password1": "complexpass123",  # pragma: allowlist secret
                    "password2": "complexpass123",  # pragma: allowlist secret
                },
            )
            assert resp.status_code == 302

        usernames = set(User.objects.values_list("username", flat=True))
        # admin + alice + alice-1
        assert "alice" in usernames
        assert "alice-1" in usernames
