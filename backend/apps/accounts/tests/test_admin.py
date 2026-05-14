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
    def test_admin_add_requires_username(self, admin_client):
        """Operator must supply the username; no derivation."""
        url = reverse("admin:accounts_user_add")
        resp = admin_client.post(
            url,
            {
                "email": "newuser@example.com",
                "username": "newuser",
                "password1": "complexpass123",  # pragma: allowlist secret
                "password2": "complexpass123",  # pragma: allowlist secret
            },
        )
        assert resp.status_code == 302, getattr(resp, "context", None)

        user = User.objects.get(email="newuser@example.com")
        assert user.username == "newuser"

    def test_admin_add_allows_reserved_handle(self, admin_client):
        """Reserved-list is operator-skipped; pin this so it can't silently
        regress (e.g. if someone wires reserved-check into a base form)."""
        url = reverse("admin:accounts_user_add")
        resp = admin_client.post(
            url,
            {
                "email": "ops@example.com",
                "username": "admin",
                "password1": "complexpass123",  # pragma: allowlist secret
                "password2": "complexpass123",  # pragma: allowlist secret
            },
        )
        assert resp.status_code == 302, getattr(resp, "context", None)
        assert User.objects.filter(username="admin").exists()
