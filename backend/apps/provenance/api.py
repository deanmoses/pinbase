"""API endpoints for the provenance app.

One router: sources.
Wired into the main NinjaAPI instance in config/api.py.
"""

from __future__ import annotations

from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view


class SourceSchema(Schema):
    name: str
    slug: str
    source_type: str
    priority: int
    url: str
    description: str


sources_router = Router(tags=["sources"])


@sources_router.get("/", response=list[SourceSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_sources(request):
    from .models import Source

    return list(Source.objects.all())
