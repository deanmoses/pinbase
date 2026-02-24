"""API endpoints for the catalog app.

Routers: models, games (titles), manufacturers, people, themes, systems, series.
Wired into the main NinjaAPI instance in config/api.py.
"""

from __future__ import annotations

from typing import Any, Optional

from django.core.cache import cache
from django.db.models import (
    Case,
    Count,
    F,
    IntegerField,
    Prefetch,
    Q,
    TextField,
    Value,
    When,
)
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view
from ninja.errors import HttpError
from ninja.pagination import PageNumberPagination, paginate
from ninja.security import django_auth

from .cache import (
    MANUFACTURERS_ALL_KEY,
    MODELS_ALL_KEY,
    PEOPLE_ALL_KEY,
    invalidate_all,
)

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
    machine_type: str
    thumbnail_url: str | None = None


class ManufacturerEntitySchema(Schema):
    name: str
    ipdb_manufacturer_id: Optional[int] = None
    years_active: str


class ManufacturerDetailSchema(Schema):
    name: str
    slug: str
    trade_name: str
    opdb_manufacturer_id: Optional[int] = None
    description: str = ""
    founded_year: int | None = None
    dissolved_year: int | None = None
    country: str | None = None
    headquarters: str | None = None
    logo_url: str | None = None
    website: str = ""
    entities: list[ManufacturerEntitySchema]
    models: list[ManufacturerModelSchema]
    systems: list[SystemSchema]
    activity: list[ClaimSchema]


class PersonGridSchema(Schema):
    name: str
    slug: str
    credit_count: int = 0
    thumbnail_url: Optional[str] = None


class PersonSchema(Schema):
    name: str
    slug: str
    credit_count: int = 0


class PersonMachineSchema(Schema):
    model_name: str
    model_slug: str
    year: int | None = None
    roles: list[str]
    thumbnail_url: str | None = None


class PersonDetailSchema(Schema):
    name: str
    slug: str
    bio: str
    birth_year: int | None = None
    birth_month: int | None = None
    birth_day: int | None = None
    death_year: int | None = None
    death_month: int | None = None
    death_day: int | None = None
    birth_place: str | None = None
    nationality: str | None = None
    photo_url: str | None = None
    machines: list[PersonMachineSchema]
    activity: list[ClaimSchema]


class ClaimSchema(Schema):
    source_name: Optional[str] = None
    source_slug: Optional[str] = None
    user_display: Optional[str] = None  # username for user-attributed claims
    field_name: str
    value: object
    citation: str
    created_at: str
    is_winner: bool


class ClaimPatchSchema(Schema):
    fields: dict[str, Any]


class ThemeSchema(Schema):
    name: str
    slug: str


class ThemeDetailSchema(Schema):
    name: str
    slug: str
    description: str = ""
    machines: list[TitleMachineSchema]


class SystemSchema(Schema):
    name: str
    slug: str


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


class DesignCreditSchema(Schema):
    person_name: str
    person_slug: str
    role: str
    role_display: str


class AliasSchema(Schema):
    name: str
    slug: str
    variant_features: list[str] = []


class MachineModelGridSchema(Schema):
    name: str
    slug: str
    year: Optional[int] = None
    manufacturer_name: Optional[str] = None
    machine_type: str
    thumbnail_url: Optional[str] = None
    shortname: Optional[str] = None


class MachineModelListSchema(Schema):
    name: str
    slug: str
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    year: Optional[int] = None
    machine_type: str
    machine_type_slug: Optional[str] = None
    machine_type_label: str
    display_type: str
    display_type_slug: Optional[str] = None
    display_type_label: str
    ipdb_id: Optional[int] = None
    ipdb_rating: Optional[float] = None
    pinside_rating: Optional[float] = None
    themes: list[ThemeSchema] = []
    thumbnail_url: Optional[str] = None


class MachineModelDetailSchema(Schema):
    name: str
    slug: str
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    machine_type: str
    machine_type_slug: Optional[str] = None
    machine_type_label: str
    display_type: str
    display_type_slug: Optional[str] = None
    display_type_label: str
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


class TitleMachineSchema(Schema):
    name: str
    slug: str
    year: Optional[int] = None
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    machine_type: str
    thumbnail_url: Optional[str] = None


class TitleListSchema(Schema):
    name: str
    slug: str
    short_name: str
    machine_count: int = 0
    manufacturer_name: Optional[str] = None
    year: Optional[int] = None
    thumbnail_url: Optional[str] = None


class SeriesRefSchema(Schema):
    name: str
    slug: str


class TitleDetailSchema(Schema):
    name: str
    slug: str
    short_name: str
    machines: list[TitleMachineSchema]
    series: list[SeriesRefSchema] = []


class SeriesListSchema(Schema):
    name: str
    slug: str
    description: str = ""
    title_count: int = 0
    thumbnail_url: Optional[str] = None


class SeriesDetailSchema(Schema):
    name: str
    slug: str
    description: str = ""
    titles: list[TitleListSchema]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_activity(active_claims) -> list[dict]:
    """Serialize pre-fetched active claims (ordered by claim_key, -priority, -created_at)
    into the activity list format, marking the winner per claim_key."""
    winners: set[str] = set()
    activity: list[dict] = []
    for claim in active_claims:
        is_winner = claim.claim_key not in winners
        if is_winner:
            winners.add(claim.claim_key)
        activity.append(
            {
                "source_name": claim.source.name if claim.source else None,
                "source_slug": claim.source.slug if claim.source else None,
                "user_display": claim.user.username if claim.user else None,
                "field_name": claim.field_name,
                "value": claim.value,
                "citation": claim.citation,
                "created_at": claim.created_at.isoformat(),
                "is_winner": is_winner,
            }
        )
    activity.sort(key=lambda c: c["created_at"], reverse=True)
    return activity


def _claims_prefetch(to_attr: str = "active_claims"):
    """Return a Prefetch for active claims with priority annotation."""
    from apps.provenance.models import Claim

    return Prefetch(
        "claims",
        queryset=Claim.objects.filter(is_active=True)
        .select_related("source", "user")
        .annotate(
            effective_priority=Case(
                When(source__isnull=False, then=F("source__priority")),
                When(user__isnull=False, then=F("user__profile__priority")),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("claim_key", "-effective_priority", "-created_at"),
        to_attr=to_attr,
    )


def _extract_image_urls(extra_data: dict) -> tuple[str | None, str | None]:
    """Return (thumbnail_url, hero_image_url) from extra_data.

    Tries OPDB structured images first (with size variants), then falls back
    to IPDB flat URL list (same URL used for both thumbnail and hero).
    """
    # Try OPDB structured images first (have size variants).
    images = extra_data.get("images")
    if images and isinstance(images, list):
        img = None
        for candidate in images:
            if isinstance(candidate, dict) and candidate.get("primary"):
                img = candidate
                break
        if img is None:
            img = images[0] if images else None
        if isinstance(img, dict):
            urls = img.get("urls") or {}
            thumbnail = urls.get("medium") or urls.get("small")
            hero = urls.get("large") or urls.get("medium")
            if thumbnail or hero:
                return thumbnail, hero

    # Fall back to IPDB flat URL list.
    image_urls = extra_data.get("image_urls")
    if image_urls and isinstance(image_urls, list):
        first = image_urls[0]
        if isinstance(first, str) and first:
            return first, first

    return None, None


def _extract_variant_features(extra_data: dict) -> list[str]:
    """Return variant feature list from extra_data variant_features claim."""
    features = extra_data.get("variant_features")
    if not features or not isinstance(features, list):
        return []
    return [str(f) for f in features]


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
    from .models import MachineModel

    qs = (
        MachineModel.objects.select_related("manufacturer")
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
        qs = qs.filter(machine_type=type)
    if display:
        qs = qs.filter(display_type=display)
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


def _profile_slug_maps() -> tuple[dict, dict]:
    """Return (machine_type_slugs, display_type_slugs) dicts keyed by type code.

    Loads at most 9 rows total (3 machine types, 6 display types).
    """
    from apps.catalog.models import DisplayTypeProfile, MachineTypeProfile

    mt = {p.machine_type: p.slug for p in MachineTypeProfile.objects.all()}
    dt = {p.display_type: p.slug for p in DisplayTypeProfile.objects.all()}
    return mt, dt


def _serialize_model_list(pm, mt_slugs: dict, dt_slugs: dict) -> dict:
    thumbnail_url, _ = _extract_image_urls(pm.extra_data or {})
    return {
        "name": pm.name,
        "slug": pm.slug,
        "manufacturer_name": pm.manufacturer.name if pm.manufacturer else None,
        "manufacturer_slug": pm.manufacturer.slug if pm.manufacturer else None,
        "year": pm.year,
        "machine_type": pm.machine_type,
        "machine_type_slug": mt_slugs.get(pm.machine_type),
        "machine_type_label": pm.get_machine_type_display(),
        "display_type": pm.display_type,
        "display_type_slug": dt_slugs.get(pm.display_type),
        "display_type_label": pm.get_display_type_display(),
        "ipdb_id": pm.ipdb_id,
        "ipdb_rating": float(pm.ipdb_rating) if pm.ipdb_rating is not None else None,
        "pinside_rating": float(pm.pinside_rating)
        if pm.pinside_rating is not None
        else None,
        "themes": [{"name": t.name, "slug": t.slug} for t in pm.themes.all()],
        "thumbnail_url": thumbnail_url,
    }


def _serialize_model_detail(pm, mt_slugs: dict, dt_slugs: dict) -> dict:
    """Serialize a MachineModel into the detail response dict.

    Expects *pm* to have been fetched with prefetch_related for credits
    (with select_related("person")) and claims (to_attr="active_claims").
    See get_model() for the canonical queryset.
    """
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
        "machine_type": pm.machine_type,
        "machine_type_slug": mt_slugs.get(pm.machine_type),
        "machine_type_label": pm.get_machine_type_display(),
        "display_type": pm.display_type,
        "display_type_slug": dt_slugs.get(pm.display_type),
        "display_type_label": pm.get_display_type_display(),
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
    }


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
    machines = []
    for pm in title.machine_models.all():
        thumbnail_url, _ = _extract_image_urls(pm.extra_data or {})
        machines.append(
            {
                "name": pm.name,
                "slug": pm.slug,
                "year": pm.year,
                "manufacturer_name": pm.manufacturer.name if pm.manufacturer else None,
                "manufacturer_slug": pm.manufacturer.slug if pm.manufacturer else None,
                "machine_type": pm.machine_type,
                "thumbnail_url": thumbnail_url,
            }
        )
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


# ---------------------------------------------------------------------------
# Models router
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
    mt_slugs, dt_slugs = _profile_slug_maps()
    return [_serialize_model_list(pm, mt_slugs, dt_slugs) for pm in qs]


@models_router.get("/all/", response=list[MachineModelGridSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_all_models(request):
    """Return every non-alias model with minimal fields (no pagination)."""
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
                "machine_type": pm.machine_type,
                "thumbnail_url": thumbnail_url,
                "shortname": pm.extra_data.get("shortname") or None,
            }
        )
    cache.set(MODELS_ALL_KEY, result, timeout=None)
    return result


@models_router.get("/{slug}", response=MachineModelDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_model(request, slug: str):
    from .models import DesignCredit, MachineModel

    pm = get_object_or_404(
        MachineModel.objects.select_related(
            "manufacturer", "title", "system"
        ).prefetch_related(
            "aliases",
            "themes",
            Prefetch(
                "credits",
                queryset=DesignCredit.objects.select_related("person"),
            ),
            _claims_prefetch(),
        ),
        slug=slug,
    )
    mt_slugs, dt_slugs = _profile_slug_maps()
    return _serialize_model_detail(pm, mt_slugs, dt_slugs)


@models_router.patch(
    "/{slug}/claims/", auth=django_auth, response=MachineModelDetailSchema
)
def patch_model_claims(request, slug: str, data: ClaimPatchSchema):
    """Assert per-field claims from the authenticated user, then re-resolve the model."""
    from apps.provenance.models import Claim

    from .models import DesignCredit, MachineModel
    from .resolve import DIRECT_FIELDS, resolve_model

    editable_fields = set(DIRECT_FIELDS.keys())
    unknown = set(data.fields.keys()) - editable_fields
    if unknown:
        raise HttpError(422, f"Unknown or non-editable fields: {sorted(unknown)}")

    pm = get_object_or_404(MachineModel, slug=slug)

    for field_name, value in data.fields.items():
        Claim.objects.assert_claim(pm, field_name, value, user=request.user)

    resolve_model(pm)
    invalidate_all()

    pm = get_object_or_404(
        MachineModel.objects.select_related(
            "manufacturer", "title", "system"
        ).prefetch_related(
            "aliases",
            "themes",
            Prefetch(
                "credits",
                queryset=DesignCredit.objects.select_related("person"),
            ),
            _claims_prefetch(),
        ),
        slug=slug,
    )
    mt_slugs, dt_slugs = _profile_slug_maps()
    return _serialize_model_detail(pm, mt_slugs, dt_slugs)


# ---------------------------------------------------------------------------
# Games (Titles) router
# ---------------------------------------------------------------------------

games_router = Router(tags=["games"])


@games_router.get("/", response=list[TitleListSchema])
@paginate(PageNumberPagination, page_size=25)
def list_games(request, search: str = ""):
    from .models import MachineModel, Title

    qs = Title.objects.annotate(
        machine_count=Count(
            "machine_models", filter=Q(machine_models__alias_of__isnull=True)
        )
    ).prefetch_related(
        Prefetch(
            "machine_models",
            queryset=MachineModel.objects.filter(alias_of__isnull=True)
            .select_related("manufacturer")
            .order_by("year", "name"),
        )
    )
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(short_name__icontains=search))
    qs = qs.order_by("name")
    return [_serialize_title_list(t) for t in qs]


@games_router.get("/all/", response=list[TitleListSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_all_games(request):
    """Return every title with minimal fields (no pagination)."""
    from .models import MachineModel, Title

    qs = (
        Title.objects.annotate(
            machine_count=Count(
                "machine_models", filter=Q(machine_models__alias_of__isnull=True)
            )
        )
        .prefetch_related(
            Prefetch(
                "machine_models",
                queryset=MachineModel.objects.filter(alias_of__isnull=True)
                .select_related("manufacturer")
                .order_by("year", "name"),
            )
        )
        .order_by("-machine_count")
    )
    return [_serialize_title_list(t) for t in qs]


@games_router.get("/{slug}", response=TitleDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_game(request, slug: str):
    from .models import MachineModel, Title

    title = get_object_or_404(
        Title.objects.prefetch_related(
            Prefetch(
                "machine_models",
                queryset=MachineModel.objects.filter(
                    alias_of__isnull=True
                ).select_related("manufacturer"),
            ),
            "series",
        ),
        slug=slug,
    )
    return _serialize_title_detail(title)


# ---------------------------------------------------------------------------
# Themes router
# ---------------------------------------------------------------------------

themes_router = Router(tags=["themes"])


@themes_router.get("/{slug}", response=ThemeDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_theme(request, slug: str):
    from .models import MachineModel, Theme

    theme = get_object_or_404(
        Theme.objects.prefetch_related(
            Prefetch(
                "machine_models",
                queryset=MachineModel.objects.filter(alias_of__isnull=True)
                .select_related("manufacturer")
                .order_by(F("year").desc(nulls_last=True), "name"),
            )
        ),
        slug=slug,
    )
    return _serialize_theme_detail(theme)


def _serialize_theme_detail(theme) -> dict:
    machines = []
    for pm in theme.machine_models.all():
        thumbnail_url, _ = _extract_image_urls(pm.extra_data or {})
        machines.append(
            {
                "name": pm.name,
                "slug": pm.slug,
                "year": pm.year,
                "manufacturer_name": pm.manufacturer.name if pm.manufacturer else None,
                "manufacturer_slug": pm.manufacturer.slug if pm.manufacturer else None,
                "machine_type": pm.machine_type,
                "thumbnail_url": thumbnail_url,
            }
        )
    return {
        "name": theme.name,
        "slug": theme.slug,
        "description": theme.description,
        "machines": machines,
    }


# ---------------------------------------------------------------------------
# Manufacturers router
# ---------------------------------------------------------------------------

manufacturers_router = Router(tags=["manufacturers"])


@manufacturers_router.get("/", response=list[ManufacturerSchema])
@paginate(PageNumberPagination, page_size=50)
def list_manufacturers(request):
    from .models import Manufacturer

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

    from .models import MachineModel, Manufacturer

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


def _serialize_manufacturer_detail(mfr) -> dict:
    """Serialize a Manufacturer into the detail response dict.

    Expects *mfr* to have been fetched with prefetch_related for entities,
    non_alias_models, and claims (to_attr="active_claims").
    """
    return {
        "name": mfr.name,
        "slug": mfr.slug,
        "trade_name": mfr.trade_name,
        "opdb_manufacturer_id": mfr.opdb_manufacturer_id,
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
                "ipdb_manufacturer_id": e.ipdb_manufacturer_id,
                "years_active": e.years_active,
            }
            for e in mfr.entities.all()
        ],
        "models": [
            {
                "name": m.name,
                "slug": m.slug,
                "year": m.year,
                "machine_type": m.machine_type,
                "thumbnail_url": _extract_image_urls(m.extra_data or {})[0],
            }
            for m in mfr.non_alias_models
        ],
        "systems": [{"name": s.name, "slug": s.slug} for s in mfr.systems.all()],
        "activity": _build_activity(getattr(mfr, "active_claims", [])),
    }


def _manufacturer_qs():
    from .models import MachineModel, Manufacturer, ManufacturerEntity, System

    return Manufacturer.objects.prefetch_related(
        Prefetch(
            "entities",
            queryset=ManufacturerEntity.objects.order_by("years_active"),
        ),
        Prefetch(
            "models",
            queryset=MachineModel.objects.filter(alias_of__isnull=True).order_by(
                F("year").desc(nulls_last=True), "name"
            ),
            to_attr="non_alias_models",
        ),
        Prefetch("systems", queryset=System.objects.order_by("name")),
        _claims_prefetch(),
    )


@manufacturers_router.get("/{slug}", response=ManufacturerDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_manufacturer(request, slug: str):
    mfr = get_object_or_404(_manufacturer_qs(), slug=slug)
    return _serialize_manufacturer_detail(mfr)


@manufacturers_router.patch(
    "/{slug}/claims/", auth=django_auth, response=ManufacturerDetailSchema
)
def patch_manufacturer_claims(request, slug: str, data: ClaimPatchSchema):
    """Assert per-field claims from the authenticated user, then re-resolve the manufacturer."""
    from apps.provenance.models import Claim

    from .models import Manufacturer
    from .resolve import MANUFACTURER_DIRECT_FIELDS, resolve_manufacturer

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


# ---------------------------------------------------------------------------
# People router
# ---------------------------------------------------------------------------

people_router = Router(tags=["people"])


@people_router.get("/", response=list[PersonSchema])
@paginate(PageNumberPagination, page_size=50)
def list_people(request):
    from .models import Person

    return list(
        Person.objects.annotate(credit_count=Count("credits"))
        .order_by("name")
        .values("name", "slug", "credit_count")
    )


@people_router.get("/all/", response=list[PersonGridSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_all_people(request):
    """Return every person with credit count and thumbnail (no pagination)."""
    result = cache.get(PEOPLE_ALL_KEY)
    if result is not None:
        return result

    from .models import Person

    people = list(
        Person.objects.annotate(credit_count=Count("credits"))
        .prefetch_related("credits__model")
        .order_by("-credit_count")
    )
    result = []
    for p in people:
        thumb = None
        # Thumbnail from most recent credited machine with image data.
        for c in sorted(p.credits.all(), key=lambda c: c.model.year or 0, reverse=True):
            if c.model.extra_data:
                t, _ = _extract_image_urls(c.model.extra_data)
                if t:
                    thumb = t
                    break
        result.append(
            {
                "name": p.name,
                "slug": p.slug,
                "credit_count": p.credit_count,
                "thumbnail_url": thumb,
            }
        )
    cache.set(PEOPLE_ALL_KEY, result, timeout=None)
    return result


def _serialize_person_detail(person) -> dict:
    """Serialize a Person into the detail response dict.

    Expects *person* to have been fetched with prefetch_related for credits
    (select_related model) and claims (to_attr="active_claims").
    """
    machines: dict[str, dict] = {}
    for c in person.credits.all():
        slug_key = c.model.slug
        if slug_key not in machines:
            thumbnail_url, _ = _extract_image_urls(c.model.extra_data or {})
            machines[slug_key] = {
                "model_name": c.model.name,
                "model_slug": slug_key,
                "year": c.model.year,
                "roles": [],
                "thumbnail_url": thumbnail_url,
            }
        machines[slug_key]["roles"].append(c.get_role_display())
    return {
        "name": person.name,
        "slug": person.slug,
        "bio": person.bio,
        "birth_year": person.birth_year,
        "birth_month": person.birth_month,
        "birth_day": person.birth_day,
        "death_year": person.death_year,
        "death_month": person.death_month,
        "death_day": person.death_day,
        "birth_place": person.birth_place,
        "nationality": person.nationality,
        "photo_url": person.photo_url,
        "machines": list(machines.values()),
        "activity": _build_activity(getattr(person, "active_claims", [])),
    }


def _person_qs():
    from .models import DesignCredit, Person

    return Person.objects.prefetch_related(
        Prefetch(
            "credits",
            queryset=DesignCredit.objects.select_related("model").order_by(
                F("model__year").desc(nulls_last=True), "model__name"
            ),
        ),
        _claims_prefetch(),
    )


@people_router.get("/{slug}", response=PersonDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_person(request, slug: str):
    person = get_object_or_404(_person_qs(), slug=slug)
    return _serialize_person_detail(person)


@people_router.patch("/{slug}/claims/", auth=django_auth, response=PersonDetailSchema)
def patch_person_claims(request, slug: str, data: ClaimPatchSchema):
    """Assert per-field claims from the authenticated user, then re-resolve the person."""
    from apps.provenance.models import Claim

    from .models import Person
    from .resolve import PERSON_DIRECT_FIELDS, resolve_person

    editable_fields = set(PERSON_DIRECT_FIELDS.keys())
    unknown = set(data.fields.keys()) - editable_fields
    if unknown:
        raise HttpError(422, f"Unknown or non-editable fields: {sorted(unknown)}")

    person = get_object_or_404(Person, slug=slug)

    for field_name, value in data.fields.items():
        Claim.objects.assert_claim(person, field_name, value, user=request.user)

    resolve_person(person)
    invalidate_all()

    person = get_object_or_404(_person_qs(), slug=person.slug)
    return _serialize_person_detail(person)


# ---------------------------------------------------------------------------
# Systems router
# ---------------------------------------------------------------------------

systems_router = Router(tags=["systems"])


@systems_router.get("/all/", response=list[SystemListSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_all_systems(request):
    """Return every system with machine count (no pagination)."""
    from .models import System

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
    from .models import MachineModel, System

    system = get_object_or_404(
        System.objects.select_related("manufacturer").prefetch_related(
            Prefetch(
                "machine_models",
                queryset=MachineModel.objects.filter(alias_of__isnull=True)
                .select_related("manufacturer")
                .order_by(F("year").desc(nulls_last=True), "name"),
            )
        ),
        slug=slug,
    )
    machines = []
    for pm in system.machine_models.all():
        thumbnail_url, _ = _extract_image_urls(pm.extra_data or {})
        machines.append(
            {
                "name": pm.name,
                "slug": pm.slug,
                "year": pm.year,
                "manufacturer_name": pm.manufacturer.name if pm.manufacturer else None,
                "manufacturer_slug": pm.manufacturer.slug if pm.manufacturer else None,
                "machine_type": pm.machine_type,
                "thumbnail_url": thumbnail_url,
            }
        )
    return {
        "name": system.name,
        "slug": system.slug,
        "description": system.description,
        "manufacturer_name": system.manufacturer.name if system.manufacturer else None,
        "manufacturer_slug": system.manufacturer.slug if system.manufacturer else None,
        "machines": machines,
    }


# ---------------------------------------------------------------------------
# Series router
# ---------------------------------------------------------------------------

series_router = Router(tags=["series"])


@series_router.get("/", response=list[SeriesListSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_series(request):
    """Return all series with title count and thumbnail."""
    from .models import MachineModel, Series

    qs = Series.objects.annotate(title_count=Count("titles")).prefetch_related(
        Prefetch(
            "titles__machine_models",
            queryset=MachineModel.objects.filter(alias_of__isnull=True)
            .exclude(extra_data={})
            .order_by(F("year").asc(nulls_last=True))
            .only("id", "extra_data"),
        )
    )
    result = []
    for s in qs:
        thumb = None
        for title in s.titles.all():
            for pm in title.machine_models.all():
                t, _ = _extract_image_urls(pm.extra_data or {})
                if t:
                    thumb = t
                    break
            if thumb:
                break
        result.append(
            {
                "name": s.name,
                "slug": s.slug,
                "description": s.description,
                "title_count": s.title_count,
                "thumbnail_url": thumb,
            }
        )
    return result


@series_router.get("/{slug}", response=SeriesDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_series(request, slug: str):
    from .models import MachineModel, Series, Title

    titles_qs = Title.objects.annotate(
        machine_count=Count(
            "machine_models",
            filter=Q(machine_models__alias_of__isnull=True),
        )
    ).prefetch_related(
        Prefetch(
            "machine_models",
            queryset=MachineModel.objects.filter(alias_of__isnull=True)
            .select_related("manufacturer")
            .order_by("year", "name"),
        )
    )
    series = get_object_or_404(
        Series.objects.prefetch_related(Prefetch("titles", queryset=titles_qs)),
        slug=slug,
    )
    return {
        "name": series.name,
        "slug": series.slug,
        "description": series.description,
        "titles": [_serialize_title_list(t) for t in series.titles.all()],
    }


# ---------------------------------------------------------------------------
# Machine types
# ---------------------------------------------------------------------------

machine_types_router = Router()


class MachineTypeProfileSchema(Schema):
    machine_type: str
    slug: str
    title: str
    display_order: int
    description: str


@machine_types_router.get("/", response=list[MachineTypeProfileSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_machine_types(request):
    from apps.catalog.models import MachineTypeProfile

    return list(MachineTypeProfile.objects.all())


@machine_types_router.get("/{slug}", response=MachineTypeProfileSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_machine_type(request, slug: str):
    from apps.catalog.models import MachineTypeProfile

    return get_object_or_404(MachineTypeProfile, slug=slug)


# ---------------------------------------------------------------------------
# Display types
# ---------------------------------------------------------------------------

display_types_router = Router()


class DisplayTypeProfileSchema(Schema):
    display_type: str
    slug: str
    title: str
    display_order: int
    description: str


@display_types_router.get("/", response=list[DisplayTypeProfileSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_display_types(request):
    from apps.catalog.models import DisplayTypeProfile

    return list(DisplayTypeProfile.objects.all())


@display_types_router.get("/{slug}", response=DisplayTypeProfileSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_display_type(request, slug: str):
    from apps.catalog.models import DisplayTypeProfile

    return get_object_or_404(DisplayTypeProfile, slug=slug)
