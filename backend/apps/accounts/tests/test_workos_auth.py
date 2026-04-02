"""Tests for the WorkOS AuthKit integration (login, callback, logout)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


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


def _make_auth_response(workos_user=None, sid="sess_01XYZ"):
    """Build a fake WorkOS authenticate_with_code response."""
    if workos_user is None:
        workos_user = _make_workos_user()

    # Build a minimal JWT with a sid claim (header.payload.signature)
    import base64
    import json

    payload = (
        base64.urlsafe_b64encode(json.dumps({"sid": sid}).encode())
        .rstrip(b"=")
        .decode()
    )
    fake_jwt = f"header.{payload}.signature"

    return SimpleNamespace(
        user=workos_user,
        access_token=fake_jwt,
        refresh_token="rt_fake",
    )


@pytest.fixture(autouse=True)
def _workos_settings(settings):
    """Ensure WorkOS settings are populated for all tests in this module."""
    settings.WORKOS_API_KEY = "sk_test_fake"  # pragma: allowlist secret
    settings.WORKOS_CLIENT_ID = "client_fake"
    settings.WORKOS_REDIRECT_URI = "http://localhost:8000/api/auth/callback/"


def _start_login(client: Client, next_url: str = "/") -> tuple[str, str]:
    """Hit the login endpoint and return (state, redirect_url).

    Follows the redirect to extract the state parameter that was stored
    in the session.
    """
    resp = client.get(f"/api/auth/login/?next={next_url}")
    assert resp.status_code == 302

    # The state is embedded in the WorkOS redirect URL as a query param
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

        # Session should have an auth_{state} key
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
    def _do_callback(self, client, *, workos_user=None, sid="sess_01XYZ"):
        """Run the full login→callback flow with mocked WorkOS."""
        auth_response = _make_auth_response(workos_user=workos_user, sid=sid)

        with patch("apps.accounts.api.get_workos_client") as mock:
            mock_client = mock.return_value
            # Echo back the real state so _start_login can parse it
            mock_client.user_management.get_authorization_url.side_effect = (
                lambda **kwargs: (
                    f"https://auth.workos.com/authorize?state={kwargs['state']}"
                )
            )
            # Start the login to populate session state
            state, _ = _start_login(client, next_url="/")

            # Now mock the code exchange
            mock_client.user_management.authenticate_with_code.return_value = (
                auth_response
            )
            resp = client.get(f"/api/auth/callback/?code=fake&state={state}")

        return resp

    def test_callback_creates_new_user(self, client):
        resp = self._do_callback(client)
        assert resp.status_code == 302

        user = User.objects.get(email="alice@example.com")
        assert user.profile.workos_user_id == "user_01ABC"
        assert user.first_name == "Alice"

    def test_callback_links_existing_user_by_email(self, client):
        existing = User.objects.create_user(username="alice", email="alice@example.com")
        resp = self._do_callback(client)
        assert resp.status_code == 302

        existing.profile.refresh_from_db()
        assert existing.profile.workos_user_id == "user_01ABC"
        # No new user should have been created
        assert User.objects.filter(email="alice@example.com").count() == 1

    def test_callback_refuses_link_unverified_email(self, client):
        existing = User.objects.create_user(username="alice", email="alice@example.com")
        workos_user = _make_workos_user(email_verified=False)
        self._do_callback(client, workos_user=workos_user)

        # Should have created a NEW user, not linked the existing one
        existing.profile.refresh_from_db()
        assert existing.profile.workos_user_id is None
        assert User.objects.filter(email="alice@example.com").count() == 2

    def test_callback_refuses_link_ambiguous_email(self, client):
        User.objects.create_user(username="alice1", email="alice@example.com")
        User.objects.create_user(username="alice2", email="alice@example.com")
        self._do_callback(client)

        # Should have created a third user, not linked either existing one
        assert User.objects.filter(email="alice@example.com").count() == 3

    def test_callback_recognizes_returning_user(self, client):
        user = User.objects.create_user(username="alice", email="alice@example.com")
        user.profile.workos_user_id = "user_01ABC"
        user.profile.save(update_fields=["workos_user_id"])

        self._do_callback(client)

        # Same user, no new user created
        assert User.objects.filter(email="alice@example.com").count() == 1

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

    def test_callback_stores_workos_session_id(self, client):
        self._do_callback(client, sid="sess_test_123")
        assert client.session.get("workos_session_id") == "sess_test_123"

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


def _set_session_value(client, key, value):
    """Persist a value into the test client's server-side session.

    Django's test client returns a *new* SessionStore each time you
    access ``client.session``, so you must save through the store
    retrieved from the session key in the cookie.
    """
    from django.contrib.sessions.backends.db import SessionStore

    session_key = client.cookies["sessionid"].value
    s = SessionStore(session_key=session_key)
    s[key] = value
    s.save()


@pytest.mark.django_db
class TestAuthLogout:
    def test_logout_returns_workos_logout_url(self, client):
        user = User.objects.create_user(username="alice")
        client.force_login(user)
        _set_session_value(client, "workos_session_id", "sess_abc")

        with patch("apps.accounts.api.get_workos_client") as mock:
            mock.return_value.user_management.get_logout_url.return_value = (
                "https://auth.workos.com/logout?sid=sess_abc"
            )
            resp = client.post("/api/auth/logout/")

        data = resp.json()
        assert data["is_authenticated"] is False
        assert "workos.com/logout" in data["logout_url"]

    def test_logout_without_workos_session(self, client):
        user = User.objects.create_user(username="alice")
        client.force_login(user)

        resp = client.post("/api/auth/logout/")
        data = resp.json()
        assert data["is_authenticated"] is False
        assert data["logout_url"] == ""

    def test_logout_multi_device(self, client):
        """Two browser sessions for the same user get independent logout URLs."""
        user = User.objects.create_user(username="alice")

        # Browser A
        client_a = Client()
        client_a.force_login(user)
        _set_session_value(client_a, "workos_session_id", "sess_A")

        # Browser B
        client_b = Client()
        client_b.force_login(user)
        _set_session_value(client_b, "workos_session_id", "sess_B")

        with patch("apps.accounts.api.get_workos_client") as mock:
            mock.return_value.user_management.get_logout_url.side_effect = (
                lambda session_id: f"https://auth.workos.com/logout?sid={session_id}"
            )
            resp_a = client_a.post("/api/auth/logout/")
            resp_b = client_b.post("/api/auth/logout/")

        assert "sess_A" in resp_a.json()["logout_url"]
        assert "sess_B" in resp_b.json()["logout_url"]


@pytest.mark.django_db
class TestAuthMe:
    def test_me_anonymous(self, client):
        resp = client.get("/api/auth/me/")
        data = resp.json()
        assert data["is_authenticated"] is False

    def test_me_authenticated(self, client):
        user = User.objects.create_user(username="alice")
        client.force_login(user)
        resp = client.get("/api/auth/me/")
        data = resp.json()
        assert data["is_authenticated"] is True
        assert data["username"] == "alice"
