"""Manufacturers router — list, detail, and claim-patch endpoints."""

from __future__ import annotations

from typing import Optional

from django.core.cache import cache
from django.db.models import Count, F, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view
from ninja.errors import HttpError
from ninja.pagination import PageNumberPagination, paginate
from ninja.security import django_auth

from ..cache import MANUFACTURERS_ALL_KEY, invalidate_all
from .helpers import _build_activity, _claims_prefetch, _extract_image_urls
from .schemas import ClaimPatchSchema, ClaimSchema

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ManufacturerGridSchema(Schema):
    name: str
    slug: str
    trade_name: str
    model_count: int = 0
    thumbnail_url: Optional[str] = None


class ManufacturerSchema(Schema):
    name: str
    slug: str
    trade_name: str
    model_count: int = 0


class ManufacturerModelSchema(Schema):
    name: str
    slug: str
    year: Optional[int] = None
    technology_generation_name: Optional[str] = None
    thumbnail_url: str | None = None


class AddressSchema(Schema):
    city: str
    state: str
    country: str


class CorporateEntitySchema(Schema):
    name: str
    years_active: str
    addresses: list[AddressSchema]


class SystemSchema(Schema):
    name: str
    slug: str


class ManufacturerDetailSchema(Schema):
    name: str
    slug: str
    trade_name: str
    description: str = ""
    founded_year: int | None = None
    dissolved_year: int | None = None
    country: str | None = None
    headquarters: str | None = None
    logo_url: str | None = None
    website: str = ""
    entities: list[CorporateEntitySchema]
    models: list[ManufacturerModelSchema]
    systems: list[SystemSchema]
    activity: list[ClaimSchema]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_manufacturer_detail(mfr) -> dict:
    """Serialize a Manufacturer into the detail response dict.

    Expects *mfr* to have been fetched with prefetch_related for entities,
    non_alias_models, and claims (to_attr="active_claims").
    """
    return {
        "name": mfr.name,
        "slug": mfr.slug,
        "trade_name": mfr.trade_name,
        "description": mfr.description,
        "founded_year": mfr.founded_year,
        "dissolved_year": mfr.dissolved_year,
        "country": mfr.country,
        "headquarters": mfr.headquarters,
        "logo_url": mfr.logo_url,
        "website": mfr.website,
        "entities": [
            {
                "name": e.name,
                "years_active": e.years_active,
                "addresses": [
                    {"city": a.city, "state": a.state, "country": a.country}
                    for a in e.addresses.all()
                ],
            }
            for e in mfr.entities.all()
        ],
        "models": [
            {
                "name": m.name,
                "slug": m.slug,
                "year": m.year,
                "technology_generation_name": (
                    m.technology_generation.name if m.technology_generation else None
                ),
                "thumbnail_url": _extract_image_urls(m.extra_data or {})[0],
            }
            for m in mfr.non_alias_models
        ],
        "systems": [{"name": s.name, "slug": s.slug} for s in mfr.systems.all()],
        "activity": _build_activity(getattr(mfr, "active_claims", [])),
    }


def _manufacturer_qs():
    from ..models import CorporateEntity, MachineModel, Manufacturer, System

    return Manufacturer.objects.prefetch_related(
        Prefetch(
            "entities",
            queryset=CorporateEntity.objects.prefetch_related("addresses").order_by(
                "years_active"
            ),
        ),
        Prefetch(
            "models",
            queryset=MachineModel.objects.filter(alias_of__isnull=True)
            .select_related("technology_generation")
            .order_by(F("year").desc(nulls_last=True), "name"),
            to_attr="non_alias_models",
        ),
        Prefetch("systems", queryset=System.objects.order_by("name")),
        _claims_prefetch(),
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

manufacturers_router = Router(tags=["manufacturers"])


@manufacturers_router.get("/", response=list[ManufacturerSchema])
@paginate(PageNumberPagination, page_size=50)
def list_manufacturers(request):
    from ..models import Manufacturer

    return list(
        Manufacturer.objects.annotate(model_count=Count("models"))
        .order_by("name")
        .values("name", "slug", "trade_name", "model_count")
    )


@manufacturers_router.get("/all/", response=list[ManufacturerGridSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_all_manufacturers(request):
    """Return every manufacturer with model count and thumbnail (no pagination)."""
    result = cache.get(MANUFACTURERS_ALL_KEY)
    if result is not None:
        return result

    from ..models import MachineModel, Manufacturer

    qs = (
        Manufacturer.objects.annotate(
            model_count=Count("models", filter=Q(models__alias_of__isnull=True))
        )
        .prefetch_related(
            Prefetch(
                "models",
                queryset=MachineModel.objects.filter(alias_of__isnull=True)
                .exclude(extra_data={})
                .order_by(F("year").desc(nulls_last=True))
                .only("id", "manufacturer_id", "year", "extra_data"),
                to_attr="models_with_images",
            )
        )
        .order_by("-model_count")
    )

    result = []
    for mfr in qs:
        thumb = None
        for model in mfr.models_with_images:
            thumb, _ = _extract_image_urls(model.extra_data)
            if thumb:
                break
        result.append(
            {
                "name": mfr.name,
                "slug": mfr.slug,
                "trade_name": mfr.trade_name,
                "model_count": mfr.model_count,
                "thumbnail_url": thumb,
            }
        )
    cache.set(MANUFACTURERS_ALL_KEY, result, timeout=None)
    return result


@manufacturers_router.get("/{slug}", response=ManufacturerDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_manufacturer(request, slug: str):
    mfr = get_object_or_404(_manufacturer_qs(), slug=slug)
    return _serialize_manufacturer_detail(mfr)


@manufacturers_router.patch(
    "/{slug}/claims/", auth=django_auth, response=ManufacturerDetailSchema
)
def patch_manufacturer_claims(request, slug: str, data: ClaimPatchSchema):
    """Assert per-field claims from the authenticated user, then re-resolve."""
    from apps.provenance.models import Claim

    from ..models import Manufacturer
    from ..resolve import MANUFACTURER_DIRECT_FIELDS, resolve_manufacturer

    editable_fields = set(MANUFACTURER_DIRECT_FIELDS.keys())
    unknown = set(data.fields.keys()) - editable_fields
    if unknown:
        raise HttpError(422, f"Unknown or non-editable fields: {sorted(unknown)}")

    mfr = get_object_or_404(Manufacturer, slug=slug)

    for field_name, value in data.fields.items():
        Claim.objects.assert_claim(mfr, field_name, value, user=request.user)

    resolve_manufacturer(mfr)
    invalidate_all()

    mfr = get_object_or_404(_manufacturer_qs(), slug=mfr.slug)
    return _serialize_manufacturer_detail(mfr)
