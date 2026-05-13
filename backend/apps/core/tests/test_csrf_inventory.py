"""CSRF enforcement on the Ninja API.

Django Ninja unconditionally marks every operation as ``csrf_exempt`` at
the Django middleware level, so ``CsrfViewMiddleware`` is short-circuited
for everything under ``/api/``. The session-cookie auth contract requires
that CSRF be enforced; ``NinjaCsrfMiddleware`` closes that gap by running
Django's CSRF check against a non-exempt placeholder for unsafe-method
``/api/`` requests.

These tests cover three layers:

1. Structural: ``NinjaCsrfMiddleware`` is wired in ``MIDDLEWARE``.
2. Per-route audit: every mutating ``/api/`` route is rejected by the
   middleware when invoked without a CSRF token. Catches a future route
   slipping past the path/method filter.
3. Full-stack integration: an authenticated POST against the real
   ``/api/auth/logout/`` endpoint, with and without the token, going
   through the full middleware chain and Ninja's view wrapper. This is
   the load-bearing coverage — it exercises everything the audit's
   isolated middleware call does not.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.test import Client, RequestFactory

from apps.accounts.models import User
from apps.core.authz.route_walker import iter_operations
from apps.core.middleware import NinjaCsrfMiddleware
from config.api import api


def _unreachable_response(request: HttpRequest) -> HttpResponse:
    """``get_response`` stand-in for the audit test.

    ``NinjaCsrfMiddleware.process_view`` never invokes ``get_response``
    (it only delegates to ``CsrfViewMiddleware.process_view``), so this
    is wired only to satisfy the ``__init__`` signature.
    """
    raise AssertionError("get_response should not be called by process_view")


def _unreachable_view(
    request: HttpRequest, *args: object, **kwargs: object
) -> HttpResponse:
    """``view_func`` stand-in for the audit test.

    The middleware substitutes its own internal placeholder before
    invoking ``CsrfViewMiddleware.process_view``, so this argument is
    intentionally ignored.
    """
    raise AssertionError("view_func should not be called by NinjaCsrfMiddleware")


# Matches the inventory in test_route_inventory.py — POST/PATCH/DELETE
# only. The project has zero @router.put(...) usages today; adding PUT
# would diverge from the existing inventory pattern without justification.
_MUTATING_METHODS = frozenset({"POST", "PATCH", "DELETE"})

# Hardcoded to mirror the NinjaAPI mount in backend/config/urls.py:15
# (``path("api/", api.urls)``). ``reverse()`` won't work because not
# every Ninja operation carries a ``url_name``, and the audit isn't
# load-bearing enough to justify wiring that up.
_API_MOUNT = "/api"


# Django's CSRF cookie format check requires exactly 32 alphanumeric
# chars (the unmasked secret). Used in the positive test so we don't
# have to prime the cookie via a GET first — the check validates
# ``cookie == submitted``, not token provenance.
_VALID_CSRF_TOKEN = "abcdefghijklmnopqrstuvwxyz012345"  # noqa: S105  # pragma: allowlist secret


def test_middleware_is_installed() -> None:
    """Structural guard: both CSRF middlewares are wired and correctly ordered.

    ``NinjaCsrfMiddleware`` piggybacks on Django's ``CsrfViewMiddleware``:
    the latter's ``process_request`` populates ``request.META['CSRF_COOKIE']``
    from the request's ``csrftoken`` cookie, and ``NinjaCsrfMiddleware``
    then compares that stored value against the submitted ``X-CSRFToken``.
    If Django's middleware is removed, the META key is never populated and
    every mutating request 403s with ``REASON_NO_CSRF_COOKIE`` — silent
    breakage. If the order is reversed, Django's ``process_request`` hasn't
    run when ours fires, with the same failure. A clear structural failure
    here is easier to diagnose than a flurry of 403s in integration tests.
    """
    django_csrf = "django.middleware.csrf.CsrfViewMiddleware"
    ninja_csrf = "apps.core.middleware.NinjaCsrfMiddleware"
    assert django_csrf in settings.MIDDLEWARE
    assert ninja_csrf in settings.MIDDLEWARE
    assert settings.MIDDLEWARE.index(django_csrf) < settings.MIDDLEWARE.index(
        ninja_csrf
    ), (
        f"{ninja_csrf} must come after {django_csrf} so the latter's "
        "process_request runs first and populates request.META['CSRF_COOKIE']."
    )


def test_every_mutating_api_route_is_csrf_protected() -> None:
    """Every mutating ``/api/`` route is rejected by the middleware.

    Drives ``NinjaCsrfMiddleware.process_view`` directly with a fresh
    ``RequestFactory`` request — no cookie, no header — and asserts each
    route 403s. This is structural: it proves the path/method filter
    matches every registered mutating route. End-to-end coverage of the
    full chain (including Ninja's ``csrf_exempt`` wrapper) comes from the
    integration tests below.
    """
    operations = [(m, p) for m, p, _ in iter_operations(api) if m in _MUTATING_METHODS]
    # Canary floor: matches test_route_inventory.py's ≥50 floor — loose,
    # not tight (current count is ~97). Guards against a future
    # django-ninja release shifting internals such that iter_operations
    # yields nothing and this test passes vacuously.
    assert len(operations) >= 50, (
        f"route_walker yielded only {len(operations)} mutating routes — "
        "django-ninja internals may have shifted."
    )

    # RequestFactory (not Client) on purpose. Client(enforce_csrf_checks=False)
    # — Django's default — sets request._dont_enforce_csrf_checks=True, which
    # CsrfViewMiddleware honors as a hard bypass. RequestFactory does not set
    # that flag, so the enforcement path is exercised end-to-end through our
    # middleware. The integration tests below use Client(enforce_csrf_checks=True)
    # to confirm the same behavior holds across the full middleware chain.
    factory = RequestFactory()
    method_to_factory = {
        "POST": factory.post,
        "PATCH": factory.patch,
        "DELETE": factory.delete,
    }
    middleware = NinjaCsrfMiddleware(get_response=_unreachable_response)

    unprotected: list[str] = []
    for method, path in operations:
        request = method_to_factory[method](f"{_API_MOUNT}{path}")
        response = middleware.process_view(request, _unreachable_view, (), {})
        if not isinstance(response, HttpResponseForbidden):
            unprotected.append(f"{method} {_API_MOUNT}{path} → {response!r}")

    assert not unprotected, (
        "Mutating routes that NinjaCsrfMiddleware did not reject:\n  "
        + "\n  ".join(unprotected)
    )


@pytest.mark.django_db
def test_logout_without_csrf_token_is_rejected(user: User) -> None:
    """Authenticated POST to /api/auth/logout/ without X-CSRFToken → 403.

    This is the negative half of the load-bearing coverage. Without
    ``NinjaCsrfMiddleware`` installed, this returns 200 (the bug being
    fixed). With it installed, Django's CSRF check fires and returns 403.
    """
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    response = client.post("/api/auth/logout/")

    assert response.status_code == 403, (
        f"Expected 403 (CSRF rejection) but got {response.status_code}. "
        "If 200, NinjaCsrfMiddleware is not enforcing — that IS the bug."
    )


@pytest.mark.django_db
def test_logout_with_csrf_token_succeeds(user: User) -> None:
    """Authenticated POST to /api/auth/logout/ with matching cookie+header → 2xx.

    Positive half: proves the middleware does not reject everything.
    Sets the CSRF cookie and header to the same value directly — Django's
    check validates ``cookie == submitted``, not token provenance, so a
    primer GET is unnecessary.
    """
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    client.cookies["csrftoken"] = _VALID_CSRF_TOKEN

    response = client.post(
        "/api/auth/logout/",
        HTTP_X_CSRFTOKEN=_VALID_CSRF_TOKEN,
    )

    assert 200 <= response.status_code < 300, (
        f"Expected 2xx but got {response.status_code}. "
        "Middleware is rejecting requests that carry a valid token."
    )
