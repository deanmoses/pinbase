"""Tests for the WorkOS AuthKit integration (login, callback, logout)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.accounts.test_factories import make_user


def _make_workos_user(
    *,
    id="user_01ABC",
    email="alice@example.com",
    email_verified=True,
    first_name="Alice",
    last_name="Smith",
):
    return SimpleNamespace(
        id=id,
        email=email,
        email_verified=email_verified,
        first_name=first_name,
        last_name=last_name,
    )


def _make_auth_response(workos_user=None):
    if workos_user is None:
        workos_user = _make_workos_user()
    return SimpleNamespace(
        user=workos_user,
        access_token="fake",
        refresh_token="fake",
    )


@pytest.fixture(autouse=True)
def _workos_settings(settings):
    settings.WORKOS_API_KEY = "sk_test_fake"  # pragma: allowlist secret
    settings.WORKOS_CLIENT_ID = "client_fake"
    settings.WORKOS_REDIRECT_URI = "http://localhost:5173/api/auth/callback/"


def _start_login(client: Client, next_url: str = "/") -> tuple[str, str]:
    resp = client.get(f"/api/auth/login/?next={next_url}")
    assert resp.status_code == 302

    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(resp["Location"])
    state = parse_qs(parsed.query).get("state", [""])[0]
    assert state, "Expected state parameter in WorkOS redirect URL"
    return state, resp["Location"]


@pytest.mark.django_db
class TestAuthLogin:
    def test_login_redirects_to_workos(self, client):
        with patch("apps.accounts.api.get_workos_client") as mock:
            mock.return_value.user_management.get_authorization_url.return_value = (
                "https://auth.workos.com/authorize?state=abc"
            )
            resp = client.get("/api/auth/login/?next=/titles/")

        assert resp.status_code == 302
        assert "workos.com" in resp["Location"]

    def test_login_stores_state_in_session(self, client):
        with patch("apps.accounts.api.get_workos_client") as mock:
            mock.return_value.user_management.get_authorization_url.return_value = (
                "https://auth.workos.com/authorize?state=test123"
            )
            client.get("/api/auth/login/?next=/titles/foo")

        session = client.session
        auth_keys = [k for k in session.keys() if k.startswith("auth_")]
        assert len(auth_keys) == 1
        assert session[auth_keys[0]] == "/titles/foo"

    def test_login_sanitizes_next_url(self, client):
        with patch("apps.accounts.api.get_workos_client") as mock:
            mock.return_value.user_management.get_authorization_url.return_value = (
                "https://auth.workos.com/authorize?state=abc"
            )
            client.get("/api/auth/login/?next=https://evil.com")

        session = client.session
        auth_keys = [k for k in session.keys() if k.startswith("auth_")]
        assert len(auth_keys) == 1
        assert session[auth_keys[0]] == "/"

    def test_login_returns_503_when_not_configured(self, client, settings):
        settings.WORKOS_API_KEY = ""
        settings.WORKOS_CLIENT_ID = ""
        resp = client.get("/api/auth/login/")
        assert resp.status_code == 503


@pytest.mark.django_db
class TestAuthCallback:
    def _do_callback(self, client, *, workos_user=None):
        auth_response = _make_auth_response(workos_user=workos_user)

        with patch("apps.accounts.api.get_workos_client") as mock:
            mock_client = mock.return_value
            mock_client.user_management.get_authorization_url.side_effect = (
                lambda **kwargs: (
                    f"https://auth.workos.com/authorize?state={kwargs['state']}"
                )
            )
            state, _ = _start_login(client, next_url="/")

            mock_client.user_management.authenticate_with_code.return_value = (
                auth_response
            )
            resp = client.get(f"/api/auth/callback/?code=fake&state={state}")

        return resp

    def test_callback_creates_new_user(self, client):
        resp = self._do_callback(client)
        assert resp.status_code == 302

        user = User.objects.get(email="alice@example.com")
        assert user.workos_user_id == "user_01ABC"
        assert user.first_name == "Alice"
        # The first-time-create path is a parallel write site to
        # _refresh_mirrored_fields and must persist verification at create
        # time, not just on subsequent logins — otherwise a verified SSO
        # user is 403'd by the policy gate for their entire first session.
        assert user.email_verified is True

    def test_callback_creates_new_user_unverified(self, client):
        """Inverse of the create-path mirror test.

        Email+password sign-up with WorkOS arrives unverified until the
        user clicks the verification email; the local row must reflect
        that. Distinct from the first-time-link refusal in
        _try_match_existing, which only fires when a local row already
        exists for the email. With no pre-existing row, the unverified
        user lands in the DB with email_verified=False and is gated by
        the policy layer until they verify and log in again.
        """
        workos_user = _make_workos_user(email_verified=False)
        resp = self._do_callback(client, workos_user=workos_user)
        assert resp.status_code == 302

        user = User.objects.get(email="alice@example.com")
        assert user.email_verified is False

    def test_callback_recognizes_returning_user(self, client):
        existing = make_user(email="alice@example.com", workos_user_id="user_01ABC")
        self._do_callback(client)

        assert User.objects.filter(email="alice@example.com").count() == 1
        existing.refresh_from_db()
        assert existing.workos_user_id == "user_01ABC"

    def test_callback_first_time_link_for_unbound_active_user(self, client):
        """Active non-privileged local row with no workos_user_id gets linked."""
        existing = make_user(email="alice@example.com")
        assert existing.workos_user_id is None

        resp = self._do_callback(client)
        assert resp.status_code == 302

        existing.refresh_from_db()
        assert existing.workos_user_id == "user_01ABC"
        assert User.objects.filter(email="alice@example.com").count() == 1

    def test_callback_refuses_auto_link_for_privileged_row(self, client):
        """Auto-link must NEVER inherit is_staff/is_superuser via verified email.

        Threat: typo'd or expired bootstrap email gets claimed at the IdP by
        an attacker, who then inherits admin access. Privileged rows can only
        be bound deliberately — sign in via WorkOS as a regular user first,
        then tick is_staff/is_superuser on that row in Django admin.
        """
        existing = make_user(
            email="alice@example.com",
            is_staff=True,
            is_superuser=True,
        )
        assert existing.workos_user_id is None

        resp = self._do_callback(client)
        assert resp.status_code == 400

        existing.refresh_from_db()
        assert existing.workos_user_id is None
        assert existing.is_superuser is True

    def test_callback_refuses_auto_link_for_staff_row(self, client):
        """Same protection applies to is_staff (not just is_superuser)."""
        existing = make_user(email="alice@example.com", is_staff=True)

        resp = self._do_callback(client)
        assert resp.status_code == 400

        existing.refresh_from_db()
        assert existing.workos_user_id is None

    def test_callback_first_time_link_refuses_unverified_email(self, client):
        """Bootstrap link path also requires verified inbound email."""
        make_user(email="alice@example.com")
        workos_user = _make_workos_user(email_verified=False)
        resp = self._do_callback(client, workos_user=workos_user)
        assert resp.status_code == 400
        # Row remains unbound.
        user = User.objects.get(email="alice@example.com")
        assert user.workos_user_id is None

    def test_callback_email_collision_with_active_user_refused(self, client):
        """Two WorkOS accounts claiming the same local user is refused."""
        # Existing active user with a different workos_user_id.
        make_user(email="alice@example.com", workos_user_id="user_OTHER")
        resp = self._do_callback(client)

        assert resp.status_code == 400
        assert User.objects.filter(email="alice@example.com").count() == 1

    def test_callback_reactivates_soft_deleted_user_with_verified_email(self, client):
        existing = make_user(email="alice@example.com")
        existing.is_active = False
        existing.workos_user_id = None
        existing.save()

        resp = self._do_callback(client)
        assert resp.status_code == 302

        existing.refresh_from_db()
        assert existing.is_active is True
        assert existing.workos_user_id == "user_01ABC"
        assert User.objects.filter(email="alice@example.com").count() == 1

    def test_callback_refuses_reactivation_with_unverified_email(self, client):
        existing = make_user(email="alice@example.com")
        existing.is_active = False
        existing.workos_user_id = None
        existing.save()

        workos_user = _make_workos_user(email_verified=False)
        resp = self._do_callback(client, workos_user=workos_user)

        assert resp.status_code == 400
        existing.refresh_from_db()
        assert existing.is_active is False
        assert User.objects.filter(email="alice@example.com").count() == 1

    def test_callback_refuses_when_mirror_email_collides(self, client):
        """Provider-side email change to an address already taken locally → refuse cleanly."""
        # Active workos_user_id match has email "old@example.com"; inbound
        # payload says email is now "alice@example.com" — but another local
        # row already has that email. Must refuse, not 500 on the unique index.
        make_user(email="old@example.com", workos_user_id="user_01ABC")
        make_user(email="alice@example.com", workos_user_id="user_OTHER")
        resp = self._do_callback(client)

        assert resp.status_code == 400
        # Neither row mutated.
        assert User.objects.filter(
            email="old@example.com", workos_user_id="user_01ABC"
        ).exists()

    def test_callback_refreshes_mirrored_fields(self, client):
        existing = make_user(
            email="alice@example.com",
            workos_user_id="user_01ABC",
            first_name="OldFirst",
            last_name="OldLast",
        )
        self._do_callback(client)

        existing.refresh_from_db()
        assert existing.first_name == "Alice"
        assert existing.last_name == "Smith"

    def test_callback_mirrors_email_verified_false_to_true(self, client):
        """Steady-state branch picks up a verification flip on next login."""
        existing = make_user(
            email="alice@example.com",
            workos_user_id="user_01ABC",
            email_verified=False,
        )
        # Default _make_workos_user has email_verified=True.
        self._do_callback(client)

        existing.refresh_from_db()
        assert existing.email_verified is True

    def test_callback_mirrors_email_verified_true_to_false(self, client):
        """Inverse direction: a provider-side reset must propagate too.

        E.g. the user changes their email at the IdP and WorkOS resets
        verification until the new address is confirmed.
        """
        existing = make_user(
            email="alice@example.com",
            workos_user_id="user_01ABC",
            email_verified=True,
        )
        workos_user = _make_workos_user(email_verified=False)
        self._do_callback(client, workos_user=workos_user)

        existing.refresh_from_db()
        assert existing.email_verified is False

    def test_callback_preserves_next_url(self, client):
        auth_response = _make_auth_response()

        with patch("apps.accounts.api.get_workos_client") as mock:
            mock_client = mock.return_value
            mock_client.user_management.get_authorization_url.side_effect = (
                lambda **kwargs: (
                    f"https://auth.workos.com/authorize?state={kwargs['state']}"
                )
            )
            state, _ = _start_login(client, next_url="/titles/medieval-madness")
            mock_client.user_management.authenticate_with_code.return_value = (
                auth_response
            )
            resp = client.get(f"/api/auth/callback/?code=fake&state={state}")

        assert resp.status_code == 302
        assert resp["Location"] == "/titles/medieval-madness"

    def test_callback_rejects_missing_code(self, client):
        resp = client.get("/api/auth/callback/")
        assert resp.status_code == 400

    def test_callback_rejects_invalid_state(self, client):
        resp = client.get("/api/auth/callback/?code=fake&state=bogus")
        assert resp.status_code == 400

    def test_callback_handles_code_exchange_failure(self, client):
        with patch("apps.accounts.api.get_workos_client") as mock:
            mock_client = mock.return_value
            mock_client.user_management.get_authorization_url.side_effect = (
                lambda **kwargs: (
                    f"https://auth.workos.com/authorize?state={kwargs['state']}"
                )
            )
            state, _ = _start_login(client, next_url="/")
            mock_client.user_management.authenticate_with_code.side_effect = Exception(
                "expired code"
            )
            resp = client.get(f"/api/auth/callback/?code=expired&state={state}")

        assert resp.status_code == 400
        assert b"please try again" in resp.content.lower()


@pytest.mark.django_db
class TestAuthLogout:
    def test_logout_clears_session(self, client):
        user = make_user(email="alice@example.com")
        client.force_login(user)

        resp = client.post("/api/auth/logout/")
        data = resp.json()
        assert data["is_authenticated"] is False

        resp = client.get("/api/auth/me/")
        assert resp.json()["is_authenticated"] is False


@pytest.mark.django_db
class TestAuthMe:
    def test_me_anonymous(self, client):
        resp = client.get("/api/auth/me/")
        data = resp.json()
        assert data["is_authenticated"] is False
        # Capability verdicts are exercised in test_me_capabilities.py.

    def test_me_authenticated(self, client):
        user = make_user(
            email="alice@example.com", first_name="Alice", last_name="Anderson"
        )
        client.force_login(user)
        resp = client.get("/api/auth/me/")
        data = resp.json()
        assert data["is_authenticated"] is True
        assert data["username"] == "alice"
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Anderson"
