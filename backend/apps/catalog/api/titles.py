"""Titles router — list and detail endpoints."""

from __future__ import annotations

from typing import Optional

from django.db.models import Count, F, Max, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view
from ninja.pagination import PageNumberPagination, paginate

from .helpers import _extract_image_urls, _serialize_title_machine
from .schemas import SeriesRefSchema, TitleMachineSchema

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TitleListSchema(Schema):
    name: str
    slug: str
    short_name: str
    machine_count: int = 0
    manufacturer_name: Optional[str] = None
    year: Optional[int] = None
    thumbnail_url: Optional[str] = None


class TitleDetailSchema(Schema):
    name: str
    slug: str
    short_name: str
    machines: list[TitleMachineSchema]
    series: list[SeriesRefSchema] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_title_list(title) -> dict:
    thumbnail_url = None
    manufacturer_name = None
    year = None
    machines = list(title.machine_models.all())
    if machines:
        thumbnail_url, _ = _extract_image_urls(machines[0].extra_data or {})
        first = machines[0]
        manufacturer_name = first.manufacturer.name if first.manufacturer else None
        year = first.year
    return {
        "name": title.name,
        "slug": title.slug,
        "short_name": title.short_name,
        "machine_count": title.machine_count,
        "manufacturer_name": manufacturer_name,
        "year": year,
        "thumbnail_url": thumbnail_url,
    }


def _serialize_title_detail(title) -> dict:
    machines = [_serialize_title_machine(pm) for pm in title.machine_models.all()]
    series = [
        {"name": s.name, "slug": s.slug}
        for s in getattr(title, "series_list", None) or title.series.all()
    ]
    return {
        "name": title.name,
        "slug": title.slug,
        "short_name": title.short_name,
        "machines": machines,
        "series": series,
    }


def _title_models_prefetch():
    from ..models import MachineModel

    return Prefetch(
        "machine_models",
        queryset=MachineModel.objects.filter(alias_of__isnull=True)
        .select_related("manufacturer", "technology_generation")
        .order_by("year", "name"),
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

titles_router = Router(tags=["titles"])


@titles_router.get("/", response=list[TitleListSchema])
@paginate(PageNumberPagination, page_size=25)
def list_titles(request, search: str = ""):
    from ..models import Title

    qs = Title.objects.annotate(
        machine_count=Count(
            "machine_models", filter=Q(machine_models__alias_of__isnull=True)
        )
    ).prefetch_related(_title_models_prefetch())
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(short_name__icontains=search))
    qs = qs.order_by("name")
    return [_serialize_title_list(t) for t in qs]


@titles_router.get("/all/", response=list[TitleListSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_all_titles(request):
    """Return every title with minimal fields (no pagination)."""
    from ..models import Title

    qs = (
        Title.objects.annotate(
            machine_count=Count(
                "machine_models", filter=Q(machine_models__alias_of__isnull=True)
            ),
            latest_year=Max(
                "machine_models__year",
                filter=Q(machine_models__alias_of__isnull=True),
            ),
        )
        .prefetch_related(_title_models_prefetch())
        .order_by(F("latest_year").desc(nulls_last=True), "name")
    )
    return [_serialize_title_list(t) for t in qs]


@titles_router.get("/{slug}", response=TitleDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_title(request, slug: str):
    from ..models import Title

    title = get_object_or_404(
        Title.objects.prefetch_related(_title_models_prefetch(), "series"),
        slug=slug,
    )
    return _serialize_title_detail(title)
