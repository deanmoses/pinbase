"""API endpoints for the machines app.

Five routers: models, groups, manufacturers, people, sources.
Wired into the main NinjaAPI instance in config/api.py.
"""

from __future__ import annotations

from typing import Optional

from django.db.models import Count, F, Prefetch, Q, TextField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.pagination import PageNumberPagination, paginate

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
    entities: list[ManufacturerEntitySchema]
    models: list[ManufacturerModelSchema]


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
    roles: list[str]
    thumbnail_url: str | None = None


class PersonDetailSchema(Schema):
    name: str
    slug: str
    bio: str
    machines: list[PersonMachineSchema]


class SourceSchema(Schema):
    name: str
    slug: str
    source_type: str
    priority: int
    url: str
    description: str


class ClaimSchema(Schema):
    source_name: str
    source_slug: str
    field_name: str
    value: object
    citation: str
    created_at: str
    is_winner: bool


class DesignCreditSchema(Schema):
    person_name: str
    person_slug: str
    role: str
    role_display: str


class AliasSchema(Schema):
    name: str
    slug: str
    features: list[str] = []


class PinballModelGridSchema(Schema):
    name: str
    slug: str
    year: Optional[int] = None
    manufacturer_name: Optional[str] = None
    machine_type: str
    thumbnail_url: Optional[str] = None


class PinballModelListSchema(Schema):
    name: str
    slug: str
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    year: Optional[int] = None
    machine_type: str
    display_type: str
    ipdb_id: Optional[int] = None
    ipdb_rating: Optional[float] = None
    pinside_rating: Optional[float] = None
    theme: str
    thumbnail_url: Optional[str] = None


class PinballModelDetailSchema(Schema):
    name: str
    slug: str
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    machine_type: str
    display_type: str
    player_count: Optional[int] = None
    theme: str
    production_quantity: str
    mpu: str
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
    features: list[str] = []
    aliases: list[AliasSchema] = []
    group_name: Optional[str] = None
    group_slug: Optional[str] = None


class GroupMachineSchema(Schema):
    name: str
    slug: str
    year: Optional[int] = None
    manufacturer_name: Optional[str] = None
    manufacturer_slug: Optional[str] = None
    machine_type: str
    thumbnail_url: Optional[str] = None


class GroupListSchema(Schema):
    name: str
    slug: str
    shortname: str
    machine_count: int = 0
    thumbnail_url: Optional[str] = None


class GroupDetailSchema(Schema):
    name: str
    slug: str
    shortname: str
    machines: list[GroupMachineSchema]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _extract_features(extra_data: dict) -> list[str]:
    """Return feature list from extra_data features claim."""
    features = extra_data.get("features")
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
    from .models import PinballModel

    qs = PinballModel.objects.select_related("manufacturer").filter(
        alias_of__isnull=True
    )

    if search:
        text_q = (
            Q(name__icontains=search)
            | Q(manufacturer__name__icontains=search)
            | Q(theme__icontains=search)
        )
        # Search extra_data by casting to text.
        text_q |= Q(**{"extra_data_text__icontains": search})
        qs = qs.annotate(extra_data_text=Cast("extra_data", TextField())).filter(text_q)

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


def _serialize_model_list(pm) -> dict:
    thumbnail_url, _ = _extract_image_urls(pm.extra_data or {})
    return {
        "name": pm.name,
        "slug": pm.slug,
        "manufacturer_name": pm.manufacturer.name if pm.manufacturer else None,
        "manufacturer_slug": pm.manufacturer.slug if pm.manufacturer else None,
        "year": pm.year,
        "machine_type": pm.machine_type,
        "display_type": pm.display_type,
        "ipdb_id": pm.ipdb_id,
        "ipdb_rating": float(pm.ipdb_rating) if pm.ipdb_rating is not None else None,
        "pinside_rating": float(pm.pinside_rating)
        if pm.pinside_rating is not None
        else None,
        "theme": pm.theme,
        "thumbnail_url": thumbnail_url,
    }


def _serialize_model_detail(pm) -> dict:
    credits = [
        {
            "person_name": c.person.name,
            "person_slug": c.person.slug,
            "role": c.role,
            "role_display": c.get_role_display(),
        }
        for c in pm.credits.select_related("person").all()
    ]

    # Build flat activity list from active claims, marking winners.
    # Claims are ordered by field_name then priority; first per field wins.
    winners: set[str] = set()
    activity: list[dict] = []
    for claim in (
        pm.claims.filter(is_active=True)
        .select_related("source")
        .order_by("field_name", "-source__priority", "-created_at")
    ):
        is_winner = claim.field_name not in winners
        if is_winner:
            winners.add(claim.field_name)
        activity.append(
            {
                "source_name": claim.source.name,
                "source_slug": claim.source.slug,
                "field_name": claim.field_name,
                "value": claim.value,
                "citation": claim.citation,
                "created_at": claim.created_at.isoformat(),
                "is_winner": is_winner,
            }
        )
    # Re-sort by most recent first for the timeline view.
    activity.sort(key=lambda c: c["created_at"], reverse=True)

    thumbnail_url, hero_image_url = _extract_image_urls(pm.extra_data or {})
    features = _extract_features(pm.extra_data or {})

    aliases = [
        {
            "name": alias.name,
            "slug": alias.slug,
            "features": _extract_features(alias.extra_data or {}),
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
        "display_type": pm.display_type,
        "player_count": pm.player_count,
        "theme": pm.theme,
        "production_quantity": pm.production_quantity,
        "mpu": pm.mpu,
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
        "features": features,
        "aliases": aliases,
        "group_name": pm.group.name if pm.group else None,
        "group_slug": pm.group.slug if pm.group else None,
    }


def _serialize_group_list(group) -> dict:
    thumbnail_url = None
    machines = list(group.machines.all())
    if machines:
        thumbnail_url, _ = _extract_image_urls(machines[0].extra_data or {})
    return {
        "name": group.name,
        "slug": group.slug,
        "shortname": group.shortname,
        "machine_count": group.machine_count,
        "thumbnail_url": thumbnail_url,
    }


def _serialize_group_detail(group) -> dict:
    machines = []
    for pm in group.machines.all():
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
        "name": group.name,
        "slug": group.slug,
        "shortname": group.shortname,
        "machines": machines,
    }


# ---------------------------------------------------------------------------
# Models router
# ---------------------------------------------------------------------------

models_router = Router(tags=["models"])


@models_router.get("/", response=list[PinballModelListSchema])
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


@models_router.get("/all/", response=list[PinballModelGridSchema])
def list_all_models(request):
    """Return every non-alias model with minimal fields (no pagination)."""
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
            }
        )
    return result


@models_router.get("/{slug}", response=PinballModelDetailSchema)
def get_model(request, slug: str):
    from .models import PinballModel

    pm = get_object_or_404(
        PinballModel.objects.select_related("manufacturer", "group").prefetch_related(
            "aliases"
        ),
        slug=slug,
    )
    return _serialize_model_detail(pm)


# ---------------------------------------------------------------------------
# Groups router
# ---------------------------------------------------------------------------

groups_router = Router(tags=["groups"])


@groups_router.get("/", response=list[GroupListSchema])
@paginate(PageNumberPagination, page_size=25)
def list_groups(request, search: str = ""):
    from .models import MachineGroup, PinballModel

    qs = MachineGroup.objects.annotate(
        machine_count=Count("machines", filter=Q(machines__alias_of__isnull=True))
    ).prefetch_related(
        Prefetch(
            "machines",
            queryset=PinballModel.objects.filter(alias_of__isnull=True).order_by(
                "year", "name"
            ),
        )
    )
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(shortname__icontains=search))
    qs = qs.order_by("name")
    return [_serialize_group_list(g) for g in qs]


@groups_router.get("/all/", response=list[GroupListSchema])
def list_all_groups(request):
    """Return every group with minimal fields (no pagination)."""
    from .models import MachineGroup, PinballModel

    qs = (
        MachineGroup.objects.annotate(
            machine_count=Count("machines", filter=Q(machines__alias_of__isnull=True))
        )
        .prefetch_related(
            Prefetch(
                "machines",
                queryset=PinballModel.objects.filter(alias_of__isnull=True).order_by(
                    "year", "name"
                ),
            )
        )
        .order_by("-machine_count")
    )
    return [_serialize_group_list(g) for g in qs]


@groups_router.get("/{slug}", response=GroupDetailSchema)
def get_group(request, slug: str):
    from .models import MachineGroup, PinballModel

    group = get_object_or_404(
        MachineGroup.objects.prefetch_related(
            Prefetch(
                "machines",
                queryset=PinballModel.objects.filter(
                    alias_of__isnull=True
                ).select_related("manufacturer"),
            )
        ),
        slug=slug,
    )
    return _serialize_group_detail(group)


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
def list_all_manufacturers(request):
    """Return every manufacturer with model count and thumbnail (no pagination)."""
    from .models import Manufacturer

    qs = Manufacturer.objects.annotate(
        model_count=Count("models", filter=Q(models__alias_of__isnull=True))
    ).order_by("-model_count")

    result = []
    for mfr in qs:
        # Thumbnail from most recent machine with a usable image.
        thumb = None
        for extra in (
            mfr.models.filter(alias_of__isnull=True)
            .exclude(extra_data={})
            .order_by(F("year").desc(nulls_last=True))
            .values_list("extra_data", flat=True)
        ):
            thumb, _ = _extract_image_urls(extra)
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
    return result


@manufacturers_router.get("/{slug}", response=ManufacturerDetailSchema)
def get_manufacturer(request, slug: str):
    from .models import Manufacturer

    mfr = get_object_or_404(Manufacturer, slug=slug)
    entities = list(
        mfr.entities.order_by("years_active").values(
            "name", "ipdb_manufacturer_id", "years_active"
        )
    )
    return {
        "name": mfr.name,
        "slug": mfr.slug,
        "trade_name": mfr.trade_name,
        "opdb_manufacturer_id": mfr.opdb_manufacturer_id,
        "entities": entities,
        "models": [
            {
                "name": m.name,
                "slug": m.slug,
                "year": m.year,
                "machine_type": m.machine_type,
                "thumbnail_url": _extract_image_urls(m.extra_data or {})[0],
            }
            for m in mfr.models.filter(alias_of__isnull=True).order_by(
                F("year").desc(nulls_last=True), "name"
            )
        ],
    }


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
def list_all_people(request):
    """Return every person with credit count and thumbnail (no pagination)."""
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
    return result


@people_router.get("/{slug}", response=PersonDetailSchema)
def get_person(request, slug: str):
    from .models import Person

    person = get_object_or_404(Person, slug=slug)
    machines: dict[str, dict] = {}
    for c in person.credits.select_related("model").order_by("model__name"):
        slug_key = c.model.slug
        if slug_key not in machines:
            thumbnail_url, _ = _extract_image_urls(c.model.extra_data or {})
            machines[slug_key] = {
                "model_name": c.model.name,
                "model_slug": slug_key,
                "roles": [],
                "thumbnail_url": thumbnail_url,
            }
        machines[slug_key]["roles"].append(c.get_role_display())
    return {
        "name": person.name,
        "slug": person.slug,
        "bio": person.bio,
        "machines": list(machines.values()),
    }


# ---------------------------------------------------------------------------
# Sources router
# ---------------------------------------------------------------------------

sources_router = Router(tags=["sources"])


@sources_router.get("/", response=list[SourceSchema])
def list_sources(request):
    from .models import Source

    return list(Source.objects.all())
