"""Request-scoped middleware for the core app.

The audience override set here is task-local via ``contextvars``. It is
read on the same task that processed the request — there is no
``sync_to_async`` or threadpool boundary in the catalog cache hot path
that would lose it.
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.licensing import reset_kiosk_audience, set_kiosk_audience


class KioskDisplayPolicyMiddleware:
    """Mark requests from kiosk devices as the ``kiosk`` content audience.

    A device opts into kiosk mode by setting the ``mode=kiosk`` cookie
    (managed by the SvelteKit kiosk routes). For the duration of such a
    request, ``apps.core.licensing.get_minimum_display_rank()`` returns
    the most permissive rank, so unlicensed images and other restricted
    content are shown.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        token = None
        if request.COOKIES.get("mode") == "kiosk":
            token = set_kiosk_audience()
        try:
            return self.get_response(request)
        finally:
            if token is not None:
                reset_kiosk_audience(token)
