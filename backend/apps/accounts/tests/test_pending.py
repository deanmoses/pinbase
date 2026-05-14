"""Tests for the pending-session helpers in apps.accounts.pending."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from apps.accounts.pending import (
    PENDING_SESSION_KEY,
    PENDING_TTL,
    clear_pending,
    ensure_session_key,
    extract_workos_session_id,
    get_pending,
    put_pending,
)


def _make_workos_user(**overrides):
    base = {
        "id": "user_01",
        "email": "alice@example.com",
        "email_verified": True,
        "first_name": "Alice",
        "last_name": "Smith",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def request_with_session(db, rf: RequestFactory):
    """A bare HttpRequest with an attached session backend."""
    from django.contrib.sessions.backends.db import SessionStore

    req = rf.get("/")
    req.session = SessionStore()
    return req


@pytest.mark.django_db
def test_ensure_session_key_persists_anonymous_session(request_with_session):
    assert request_with_session.session.session_key is None
    key = ensure_session_key(request_with_session)
    assert key is not None
    assert request_with_session.session.session_key == key


@pytest.mark.django_db
def test_put_and_get_pending_roundtrip(request_with_session):
    put_pending(request_with_session, _make_workos_user(), "/next/")
    payload = get_pending(request_with_session)
    assert payload is not None
    assert payload["workos_user_id"] == "user_01"
    assert payload["email"] == "alice@example.com"
    assert payload["first_name"] == "Alice"
    assert payload["next_url"] == "/next/"
    assert payload["workos_session_id"] == ""


@pytest.mark.django_db
def test_put_pending_stashes_workos_session_id(request_with_session):
    put_pending(
        request_with_session,
        _make_workos_user(),
        "/",
        workos_session_id="session_xyz",
    )
    payload = get_pending(request_with_session)
    assert payload is not None
    assert payload["workos_session_id"] == "session_xyz"


@pytest.mark.django_db
def test_put_pending_handles_null_names(request_with_session):
    put_pending(
        request_with_session,
        _make_workos_user(first_name=None, last_name=None),
        "/",
    )
    payload = get_pending(request_with_session)
    assert payload is not None
    assert payload["first_name"] == ""
    assert payload["last_name"] == ""


@pytest.mark.django_db
def test_get_pending_returns_none_when_missing(request_with_session):
    assert get_pending(request_with_session) is None


@pytest.mark.django_db
def test_get_pending_clears_and_returns_none_when_expired(request_with_session):
    put_pending(request_with_session, _make_workos_user(), "/")
    # Backdate the created_at past the TTL so the freshness check trips.
    stale = (datetime.now(UTC) - PENDING_TTL - timedelta(seconds=1)).isoformat()
    request_with_session.session[PENDING_SESSION_KEY]["created_at"] = stale
    request_with_session.session.modified = True

    assert get_pending(request_with_session) is None
    # Side effect: expired payload is cleared.
    assert PENDING_SESSION_KEY not in request_with_session.session


@pytest.mark.django_db
def test_clear_pending_is_idempotent(request_with_session):
    clear_pending(request_with_session)  # no-op
    put_pending(request_with_session, _make_workos_user(), "/")
    clear_pending(request_with_session)
    assert PENDING_SESSION_KEY not in request_with_session.session


def test_extract_workos_session_id_pulls_sid_from_jwt():
    # Hand-crafted JWT: header.payload.signature; only payload matters.
    import base64
    import json

    payload = (
        base64.urlsafe_b64encode(
            json.dumps({"sid": "session_abc123", "iss": "workos"}).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    token = f"header.{payload}.signature"
    assert extract_workos_session_id(token) == "session_abc123"


def test_extract_workos_session_id_returns_empty_on_malformed_token():
    assert extract_workos_session_id("") == ""
    assert extract_workos_session_id("not-a-jwt") == ""
    assert extract_workos_session_id("a.b.c") == ""  # b isn't valid base64 JSON


def test_extract_workos_session_id_returns_empty_when_sid_missing():
    import base64
    import json

    payload = (
        base64.urlsafe_b64encode(json.dumps({"iss": "workos"}).encode())
        .rstrip(b"=")
        .decode()
    )
    token = f"header.{payload}.signature"
    assert extract_workos_session_id(token) == ""
