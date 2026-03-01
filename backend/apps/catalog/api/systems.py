"""Systems router — list and detail endpoints."""

from __future__ import annotations

from typing import Optional

from django.db.models import Count, F, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view

from .helpers import _serialize_title_machine
from .schemas import TitleMachineSchema

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SystemListSchema(Schema):
    name: str
    slug: str
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    machine_count: int = 0


class SystemDetailSchema(Schema):
    name: str
    slug: str
    description: str = ""
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    machines: list[TitleMachineSchema]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

systems_router = Router(tags=["systems"])


@systems_router.get("/all/", response=list[SystemListSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_all_systems(request):
    """Return every system with machine count (no pagination)."""
    from ..models import System

    qs = (
        System.objects.select_related("manufacturer")
        .annotate(
            machine_count=Count(
                "machine_models", filter=Q(machine_models__alias_of__isnull=True)
            )
        )
        .order_by("name")
    )
    return [
        {
            "name": s.name,
            "slug": s.slug,
            "manufacturer_name": s.manufacturer.name if s.manufacturer else None,
            "manufacturer_slug": s.manufacturer.slug if s.manufacturer else None,
            "machine_count": s.machine_count,
        }
        for s in qs
    ]


@systems_router.get("/{slug}", response=SystemDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_system(request, slug: str):
    from ..models import MachineModel, System

    system = get_object_or_404(
        System.objects.select_related("manufacturer").prefetch_related(
            Prefetch(
                "machine_models",
                queryset=MachineModel.objects.filter(alias_of__isnull=True)
                .select_related("manufacturer", "technology_generation")
                .order_by(F("year").desc(nulls_last=True), "name"),
            )
        ),
        slug=slug,
    )
    machines = [_serialize_title_machine(pm) for pm in system.machine_models.all()]
    return {
        "name": system.name,
        "slug": system.slug,
        "description": system.description,
        "manufacturer_name": system.manufacturer.name if system.manufacturer else None,
        "manufacturer_slug": system.manufacturer.slug if system.manufacturer else None,
        "machines": machines,
    }
