"""Enforce CSRF on the Ninja API.

Django Ninja stamps every view function with ``csrf_exempt = True`` at
import time (see ``ninja/operation.py``: *"All django-ninja views are
CSRF exempt at Django middleware level / Cookie-based auth (APIKeyCookie)
handles CSRF checking separately"*). With session-cookie auth and no
``APIKeyCookie`` in use, that exemption leaves every unsafe-method
``/api/`` route open to cross-site forgery from any authenticated tab.

This middleware reinstates the check for ``/api/`` requests by invoking
``CsrfViewMiddleware.process_view`` against a fresh, non-exempt
placeholder callable — bypassing Ninja's blanket exempt flag without
patching Ninja itself.
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.middleware.csrf import CsrfViewMiddleware

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _placeholder(request: HttpRequest) -> HttpResponse:
    """Non-exempt stand-in passed to ``CsrfViewMiddleware.process_view``.

    The real Ninja view is marked ``csrf_exempt = True``; passing it would
    short-circuit the check. This bare function has no such attribute, so
    Django's CSRF logic proceeds to validate cookie vs. submitted token.
    The function body is never invoked — only its identity (and lack of
    ``csrf_exempt``) matters.
    """
    raise AssertionError("placeholder should never be called")  # pragma: no cover


class NinjaCsrfMiddleware:
    """Run Django's CSRF check against unsafe-method ``/api/`` requests.

    Coexists with Django's own ``CsrfViewMiddleware`` (which sees the
    Ninja view's ``csrf_exempt`` flag and no-ops). One ``_csrf`` instance
    is reused across requests — ``CsrfViewMiddleware`` keeps no
    per-request state on the instance.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response
        self._csrf = CsrfViewMiddleware(get_response)

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        return self.get_response(request)

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable[..., HttpResponseBase],
        view_args: tuple[object, ...],
        view_kwargs: dict[str, object],
    ) -> HttpResponseBase | None:
        if not request.path.startswith("/api/"):
            return None
        if request.method in _SAFE_METHODS:
            return None
        # CsrfViewMiddleware honors ``request._dont_enforce_csrf_checks``
        # (set by Django's test ``Client`` when ``enforce_csrf_checks`` is
        # False), so tests using the default ``Client()`` keep passing.
        return self._csrf.process_view(request, _placeholder, view_args, view_kwargs)
