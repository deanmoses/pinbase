"""Tests for KioskDisplayPolicyMiddleware."""

from __future__ import annotations

import contextlib

from django.http import HttpRequest, HttpResponse

from apps.core.licensing import current_audience
from apps.core.middleware import KioskDisplayPolicyMiddleware


def _make_request(cookie: str | None = None) -> HttpRequest:
    request = HttpRequest()
    if cookie is not None:
        request.COOKIES["mode"] = cookie
    return request


class TestKioskDisplayPolicyMiddleware:
    """The middleware reads ``mode=kiosk`` cookies into the audience contextvar."""

    def test_kiosk_cookie_sets_audience_during_request(self):
        observed: list[str] = []

        def view(_request: HttpRequest) -> HttpResponse:
            observed.append(current_audience())
            return HttpResponse()

        middleware = KioskDisplayPolicyMiddleware(view)
        middleware(_make_request(cookie="kiosk"))

        assert observed == ["kiosk"]

    def test_audience_resets_after_request(self):
        middleware = KioskDisplayPolicyMiddleware(lambda _r: HttpResponse())
        middleware(_make_request(cookie="kiosk"))
        assert current_audience() == "default"

    def test_audience_resets_even_when_view_raises(self):
        class BoomError(Exception):
            pass

        def view(_request: HttpRequest) -> HttpResponse:
            raise BoomError

        middleware = KioskDisplayPolicyMiddleware(view)
        with contextlib.suppress(BoomError):
            middleware(_make_request(cookie="kiosk"))

        assert current_audience() == "default"

    def test_no_cookie_leaves_audience_default(self):
        observed: list[str] = []

        def view(_request: HttpRequest) -> HttpResponse:
            observed.append(current_audience())
            return HttpResponse()

        middleware = KioskDisplayPolicyMiddleware(view)
        middleware(_make_request(cookie=None))

        assert observed == ["default"]

    def test_unrelated_cookie_value_leaves_audience_default(self):
        observed: list[str] = []

        def view(_request: HttpRequest) -> HttpResponse:
            observed.append(current_audience())
            return HttpResponse()

        middleware = KioskDisplayPolicyMiddleware(view)
        middleware(_make_request(cookie="something-else"))

        assert observed == ["default"]
