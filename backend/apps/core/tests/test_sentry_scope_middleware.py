"""Tests for ``SentryScopeMiddleware``.

The middleware attaches per-request scope data (user + tags) when
the SDK has an active client, and is a no-op otherwise.

The ``{id, username}`` keep-list is **load-bearing** for the privacy
contract. There is no ``before_send`` scrubber to catch a mistake;
the only other safeguard preventing ``user.email`` from being sent is
``send_default_pii=False``. ``test_keep_list_is_id_and_username_only``
pins the exact shape and must not be weakened.
"""

from __future__ import annotations

import sentry_sdk
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.test import RequestFactory

from apps.accounts.test_factories import make_user
from apps.core.middleware.sentry_scope import SentryScopeMiddleware


def _noop_response(request: HttpRequest) -> HttpResponseBase:
    return HttpResponse()


def _run(request: HttpRequest) -> None:
    """Invoke the middleware once against ``request``."""
    SentryScopeMiddleware(_noop_response)(request)


# ── User attribution ───────────────────────────────────────────────


def test_authenticated_request_sets_user_id_and_username(
    db: None, sentry_active: None
) -> None:
    """``isolation_scope`` gives the test a fresh per-request scope
    matching what ``DjangoIntegration`` builds at runtime. Reads off
    the same scope object verify exactly what the middleware wrote.
    """
    user = make_user(username="alice")
    request = RequestFactory().get("/")
    request.user = user

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._user == {"id": user.id, "username": "alice"}


def test_anonymous_request_attaches_no_user(sentry_active: None) -> None:
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._user is None


def test_keep_list_is_id_and_username_only(db: None, sentry_active: None) -> None:
    """The keep-list IS the privacy chokepoint for the user dict.

    Email and IP are explicitly *not* sent to Sentry per Privacy.md.
    Without this test pinning the exact ``{id, username}`` shape,
    a refactor that adds ``"email": user.email`` to the middleware's
    ``set_user`` call would silently ship the email. There is no
    ``before_send`` scrubber to catch it.
    """
    user = make_user(username="alice", email="alice@example.com")
    request = RequestFactory().get("/")
    request.user = user

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._user is not None
        assert set(scope._user.keys()) == {"id", "username"}


# ── Tags ───────────────────────────────────────────────────────────


def test_authenticated_request_sets_auth_state_tag_to_auth(
    db: None, sentry_active: None
) -> None:
    user = make_user(username="alice")
    request = RequestFactory().get("/")
    request.user = user

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._tags["auth_state"] == "auth"


def test_anonymous_request_sets_auth_state_tag_to_anon(sentry_active: None) -> None:
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._tags["auth_state"] == "anon"


def test_chrome_user_agent_tags_as_chrome(sentry_active: None) -> None:
    request = RequestFactory().get("/", HTTP_USER_AGENT="Mozilla/5.0 Chrome/120.0")
    request.user = AnonymousUser()

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._tags["ua_family"] == "chrome"


def test_firefox_user_agent_tags_as_firefox(sentry_active: None) -> None:
    request = RequestFactory().get("/", HTTP_USER_AGENT="Mozilla/5.0 Firefox/115.0")
    request.user = AnonymousUser()

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._tags["ua_family"] == "firefox"


def test_bot_user_agent_tags_as_bot(sentry_active: None) -> None:
    request = RequestFactory().get(
        "/", HTTP_USER_AGENT="Googlebot/2.1 (+http://www.google.com/bot.html)"
    )
    request.user = AnonymousUser()

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._tags["ua_family"] == "bot"


def test_missing_user_agent_tags_as_unknown(sentry_active: None) -> None:
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._tags["ua_family"] == "unknown"


# ── Inactive-client no-op ──────────────────────────────────────────


def test_middleware_is_a_noop_with_inactive_client(db: None) -> None:
    """When SENTRY_DSN is unset the SDK has no active client.

    The middleware must skip every scope mutation in that case;
    otherwise it pollutes the in-process isolation scope, which a
    later SDK init in the same process (a recording-transport test,
    a debug script) would inherit. The scope must stay untouched —
    no user, no tags.
    """
    assert not sentry_sdk.get_client().is_active(), (
        "test premise: SDK must be inactive (no SENTRY_DSN in test env)"
    )
    user = make_user(username="alice")
    request = RequestFactory().get("/", HTTP_USER_AGENT="Mozilla/5.0 Chrome/120.0")
    request.user = user

    with sentry_sdk.isolation_scope() as scope:
        _run(request)
        assert scope._user is None
        assert "auth_state" not in scope._tags
        assert "ua_family" not in scope._tags
