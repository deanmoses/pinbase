"""last_seen_at writer.

Without a writer the column stays NULL forever and provides no value at
provider-switch time. Debounced to once per day per user, using the stored
field value as the debounce state — no in-memory cache that resets at boot.

Writes happen *after* the view returns, so an unhandled view exception
skips that request's update. Acceptable: this is a coarse freshness signal,
not an audit trail; missing one update has no semantic consequence.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from .models import User

_DEBOUNCE = timedelta(hours=24)


class LastSeenAtMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        # AnonymousUser has no last_seen_at — skip before attribute access.
        if request.user.is_authenticated:
            assert isinstance(request.user, User)
            now = timezone.now()
            last = request.user.last_seen_at
            if last is None or now - last >= _DEBOUNCE:
                # TODO(perf): under traffic move this off the request path
                # (transaction.on_commit or a queue). Fine at v1 scale.
                User.objects.filter(pk=request.user.pk).update(last_seen_at=now)
        return response
