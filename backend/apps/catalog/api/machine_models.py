"""Models (machine models) router — list, detail, and claim-patch endpoints."""

from __future__ import annotations

from typing import Optional

from django.db.models import F, Prefetch, Q, TextField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view
from ninja.errors import HttpError
from ninja.pagination import PageNumberPagination, paginate
from ninja.security import django_auth

from ..cache import MODELS_ALL_KEY, invalidate_all
from .helpers import (
    _build_activity,
    _claims_prefetch,
    _extract_image_urls,
    _extract_variant_features,
)
from .schemas import (
    ClaimPatchSchema,
    ClaimSchema,
    FranchiseRefSchema,
    GameplayFeatureSchema,
    SeriesRefSchema,
    ThemeSchema,
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MachineModelGridSchema(Schema):
    name: str
    slug: str
    year: Optional[int] = None
    manufacturer_name: Optional[str] = None
    technology_generation_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    shortname: Optional[str] = None


class MachineModelListSchema(Schema):
    name: str
    slug: str
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    year: Optional[int] = None
    technology_generation_name: Optional[str] = None
    technology_generation_slug: Optional[str] = None
    display_type_name: Optional[str] = None
    display_type_slug: Optional[str] = None
    ipdb_id: Optional[int] = None
    ipdb_rating: Optional[float] = None
    pinside_rating: Optional[float] = None
    themes: list[ThemeSchema] = []
    thumbnail_url: Optional[str] = None


class DesignCreditSchema(Schema):
    person_name: str
    person_slug: str
    role: str
    role_display: str


class AliasSchema(Schema):
    name: str
    slug: str
    variant_features: list[str] = []


class MachineModelDetailSchema(Schema):
    name: str
    slug: str
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    technology_generation_name: Optional[str] = None
    technology_generation_slug: Optional[str] = None
    display_type_name: Optional[str] = None
    display_type_slug: Optional[str] = None
    player_count: Optional[int] = None
    themes: list[ThemeSchema] = []
    production_quantity: str
    system_name: Optional[str] = None
    system_slug: Optional[str] = None
    flipper_count: Optional[int] = None
    ipdb_id: Optional[int] = None
    opdb_id: Optional[str] = None
    pinside_id: Optional[int] = None
    ipdb_rating: Optional[float] = None
    pinside_rating: Optional[float] = None
    educational_text: str
    sources_notes: str
    extra_data: dict
    credits: list[DesignCreditSchema]
    activity: list[ClaimSchema]
    thumbnail_url: Optional[str] = None
    hero_image_url: Optional[str] = None
    variant_features: list[str] = []
    aliases: list[AliasSchema] = []
    title_name: Optional[str] = None
    title_slug: Optional[str] = None
    cabinet_name: Optional[str] = None
    cabinet_slug: Optional[str] = None
    game_format_name: Optional[str] = None
    game_format_slug: Optional[str] = None
    display_subtype_name: Optional[str] = None
    display_subtype_slug: Optional[str] = None
    gameplay_features: list[GameplayFeatureSchema] = []
    franchise: Optional[FranchiseRefSchema] = None
    series: list[SeriesRefSchema] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_model_list_qs(
    search: str = "",
    manufacturer: str = "",
    type: str = "",
    display: str = "",
    year_min: int | None = None,
    year_max: int | None = None,
    person: str = "",
    ordering: str = "-year",
):
    from ..models import MachineModel

    qs = (
        MachineModel.objects.select_related(
            "manufacturer", "technology_generation", "display_type"
        )
        .prefetch_related("themes")
        .filter(alias_of__isnull=True)
    )

    if search:
        text_q = (
            Q(name__icontains=search)
            | Q(manufacturer__name__icontains=search)
            | Q(themes__name__icontains=search)
        )
        # Search extra_data by casting to text.
        text_q |= Q(**{"extra_data_text__icontains": search})
        qs = qs.annotate(extra_data_text=Cast("extra_data", TextField())).filter(text_q)
        qs = qs.distinct()

    if manufacturer:
        qs = qs.filter(manufacturer__slug=manufacturer)
    if type:
        qs = qs.filter(technology_generation__slug=type)
    if display:
        qs = qs.filter(display_type__slug=display)
    if year_min is not None:
        qs = qs.filter(year__gte=year_min)
    if year_max is not None:
        qs = qs.filter(year__lte=year_max)
    if person:
        qs = qs.filter(credits__person__slug=person).distinct()

    ordering_map = {
        "name": [F("name").asc()],
        "-name": [F("name").desc()],
        "year": [F("year").asc(nulls_last=True)],
        "-year": [F("year").desc(nulls_last=True)],
        "-ipdb_rating": [F("ipdb_rating").desc(nulls_last=True)],
        "-pinside_rating": [F("pinside_rating").desc(nulls_last=True)],
        "ipdb_rating": [F("ipdb_rating").asc(nulls_last=True)],
        "pinside_rating": [F("pinside_rating").asc(nulls_last=True)],
    }
    order_exprs = ordering_map.get(ordering, ordering_map["-year"])
    qs = qs.order_by(*order_exprs, "name")

    return qs


def _serialize_model_list(pm) -> dict:
    thumbnail_url, _ = _extract_image_urls(pm.extra_data or {})
    return {
        "name": pm.name,
        "slug": pm.slug,
        "manufacturer_name": pm.manufacturer.name if pm.manufacturer else None,
        "manufacturer_slug": pm.manufacturer.slug if pm.manufacturer else None,
        "year": pm.year,
        "technology_generation_name": (
            pm.technology_generation.name if pm.technology_generation else None
        ),
        "technology_generation_slug": (
            pm.technology_generation.slug if pm.technology_generation else None
        ),
        "display_type_name": pm.display_type.name if pm.display_type else None,
        "display_type_slug": pm.display_type.slug if pm.display_type else None,
        "ipdb_id": pm.ipdb_id,
        "ipdb_rating": float(pm.ipdb_rating) if pm.ipdb_rating is not None else None,
        "pinside_rating": float(pm.pinside_rating)
        if pm.pinside_rating is not None
        else None,
        "themes": [{"name": t.name, "slug": t.slug} for t in pm.themes.all()],
        "thumbnail_url": thumbnail_url,
    }


def _serialize_model_detail(pm) -> dict:
    """Serialize a MachineModel into the detail response dict.

    Expects *pm* to have been fetched with prefetch_related for credits
    (with select_related("person")) and claims (to_attr="active_claims").
    """
    from django.db.models import Case, F, IntegerField, Value, When

    credits = [
        {
            "person_name": c.person.name,
            "person_slug": c.person.slug,
            "role": c.role,
            "role_display": c.get_role_display(),
        }
        for c in pm.credits.all()
    ]

    activity_claims = getattr(pm, "active_claims", None)
    if activity_claims is None:
        activity_claims = list(
            pm.claims.filter(is_active=True)
            .select_related("source", "user")
            .annotate(
                effective_priority=Case(
                    When(source__isnull=False, then=F("source__priority")),
                    When(user__isnull=False, then=F("user__profile__priority")),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by("claim_key", "-effective_priority", "-created_at")
        )
    activity = _build_activity(activity_claims)

    thumbnail_url, hero_image_url = _extract_image_urls(pm.extra_data or {})
    variant_features = _extract_variant_features(pm.extra_data or {})

    aliases = [
        {
            "name": alias.name,
            "slug": alias.slug,
            "variant_features": _extract_variant_features(alias.extra_data or {}),
        }
        for alias in pm.aliases.all()
    ]

    return {
        "name": pm.name,
        "slug": pm.slug,
        "manufacturer_name": pm.manufacturer.name if pm.manufacturer else None,
        "manufacturer_slug": pm.manufacturer.slug if pm.manufacturer else None,
        "year": pm.year,
        "month": pm.month,
        "technology_generation_name": (
            pm.technology_generation.name if pm.technology_generation else None
        ),
        "technology_generation_slug": (
            pm.technology_generation.slug if pm.technology_generation else None
        ),
        "display_type_name": pm.display_type.name if pm.display_type else None,
        "display_type_slug": pm.display_type.slug if pm.display_type else None,
        "player_count": pm.player_count,
        "themes": [{"name": t.name, "slug": t.slug} for t in pm.themes.all()],
        "production_quantity": pm.production_quantity,
        "system_name": pm.system.name if pm.system else None,
        "system_slug": pm.system.slug if pm.system else None,
        "flipper_count": pm.flipper_count,
        "ipdb_id": pm.ipdb_id,
        "opdb_id": pm.opdb_id,
        "pinside_id": pm.pinside_id,
        "ipdb_rating": float(pm.ipdb_rating) if pm.ipdb_rating is not None else None,
        "pinside_rating": float(pm.pinside_rating)
        if pm.pinside_rating is not None
        else None,
        "educational_text": pm.educational_text,
        "sources_notes": pm.sources_notes,
        "extra_data": pm.extra_data or {},
        "credits": credits,
        "activity": activity,
        "thumbnail_url": thumbnail_url,
        "hero_image_url": hero_image_url,
        "variant_features": variant_features,
        "aliases": aliases,
        "title_name": pm.title.name if pm.title else None,
        "title_slug": pm.title.slug if pm.title else None,
        "cabinet_name": pm.cabinet.name if pm.cabinet else None,
        "cabinet_slug": pm.cabinet.slug if pm.cabinet else None,
        "game_format_name": pm.game_format.name if pm.game_format else None,
        "game_format_slug": pm.game_format.slug if pm.game_format else None,
        "display_subtype_name": (
            pm.display_subtype.name if pm.display_subtype else None
        ),
        "display_subtype_slug": (
            pm.display_subtype.slug if pm.display_subtype else None
        ),
        "gameplay_features": [
            {"name": gf.name, "slug": gf.slug} for gf in pm.gameplay_features.all()
        ],
        "franchise": (
            {"name": pm.title.franchise.name, "slug": pm.title.franchise.slug}
            if pm.title and pm.title.franchise
            else None
        ),
        "series": [
            {"name": s.name, "slug": s.slug}
            for s in (pm.title.series.all() if pm.title else [])
        ],
    }


def _model_detail_qs():
    """Return the queryset used for model detail / patch endpoints."""
    from ..models import DesignCredit, MachineModel

    return MachineModel.objects.select_related(
        "manufacturer",
        "title",
        "title__franchise",
        "system",
        "technology_generation",
        "display_type",
        "display_subtype",
        "cabinet",
        "game_format",
    ).prefetch_related(
        "aliases",
        "themes",
        "gameplay_features",
        "title__series",
        Prefetch(
            "credits",
            queryset=DesignCredit.objects.filter(model__isnull=False).select_related(
                "person"
            ),
        ),
        _claims_prefetch(),
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

models_router = Router(tags=["models"])


@models_router.get("/", response=list[MachineModelListSchema])
@paginate(PageNumberPagination, page_size=25)
def list_models(
    request,
    search: str = "",
    manufacturer: str = "",
    type: str = "",
    display: str = "",
    year_min: int | None = None,
    year_max: int | None = None,
    person: str = "",
    ordering: str = "-year",
):
    qs = _build_model_list_qs(
        search=search,
        manufacturer=manufacturer,
        type=type,
        display=display,
        year_min=year_min,
        year_max=year_max,
        person=person,
        ordering=ordering,
    )
    return [_serialize_model_list(pm) for pm in qs]


@models_router.get("/all/", response=list[MachineModelGridSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_all_models(request):
    """Return every non-alias model with minimal fields (no pagination)."""
    from django.core.cache import cache

    result = cache.get(MODELS_ALL_KEY)
    if result is not None:
        return result
    qs = _build_model_list_qs()
    result = []
    for pm in qs:
        thumbnail_url, _ = _extract_image_urls(pm.extra_data or {})
        result.append(
            {
                "name": pm.name,
                "slug": pm.slug,
                "year": pm.year,
                "manufacturer_name": (
                    pm.manufacturer.name if pm.manufacturer else None
                ),
                "technology_generation_name": (
                    pm.technology_generation.name if pm.technology_generation else None
                ),
                "thumbnail_url": thumbnail_url,
                "shortname": pm.extra_data.get("shortname") or None,
            }
        )
    cache.set(MODELS_ALL_KEY, result, timeout=None)
    return result


@models_router.get("/{slug}", response=MachineModelDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_model(request, slug: str):
    pm = get_object_or_404(_model_detail_qs(), slug=slug)
    return _serialize_model_detail(pm)


@models_router.patch(
    "/{slug}/claims/", auth=django_auth, response=MachineModelDetailSchema
)
def patch_model_claims(request, slug: str, data: ClaimPatchSchema):
    """Assert per-field claims from the authenticated user, then re-resolve the model."""
    from apps.provenance.models import Claim

    from ..models import MachineModel
    from ..resolve import DIRECT_FIELDS, resolve_model

    editable_fields = set(DIRECT_FIELDS.keys())
    unknown = set(data.fields.keys()) - editable_fields
    if unknown:
        raise HttpError(422, f"Unknown or non-editable fields: {sorted(unknown)}")

    pm = get_object_or_404(MachineModel, slug=slug)

    for field_name, value in data.fields.items():
        Claim.objects.assert_claim(pm, field_name, value, user=request.user)

    resolve_model(pm)
    invalidate_all()

    pm = get_object_or_404(_model_detail_qs(), slug=slug)
    return _serialize_model_detail(pm)
