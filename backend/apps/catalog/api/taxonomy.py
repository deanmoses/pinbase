"""Taxonomy routers — technology generations, display types, and related lookups."""

from __future__ import annotations

from django.db.models import F, Prefetch
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view
from ninja.security import django_auth

from apps.provenance.helpers import build_sources, claims_prefetch

from ._counts import bulk_title_counts_via_models
from .edit_claims import execute_claims, plan_scalar_field_claims
from .entity_crud import (
    register_entity_create,
    register_entity_delete_restore,
)

from ..models import (
    Cabinet,
    CreditRole,
    DisplaySubtype,
    DisplayType,
    GameFormat,
    MachineModel,
    RewardType,
    Tag,
    TechnologyGeneration,
    TechnologySubgeneration,
)
from apps.core.licensing import get_minimum_display_rank

from .helpers import _build_rich_text, _serialize_title_machine
from .schemas import (
    ClaimPatchSchema,
    ClaimSchema,
    RichTextSchema,
    TitleMachineSchema,
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TaxonomySchema(Schema):
    name: str
    slug: str
    display_order: int
    description: RichTextSchema = RichTextSchema()
    aliases: list[str] = []
    sources: list[ClaimSchema] = []


class TaxonomyWithTitleCountSchema(TaxonomySchema):
    title_count: int = 0


class DisplayTypeListSchema(TaxonomyWithTitleCountSchema):
    subtypes: list[TaxonomyWithTitleCountSchema] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_taxonomy(obj) -> dict:
    # Only RewardType among the shared-schema taxonomies carries aliases;
    # Tag / Cabinet / GameFormat / Tech* / Display* don't have an alias
    # model. ``hasattr`` on the class keeps the serializer uniform without
    # triggering a lookup query on the alias-less branches.
    aliases: list[str] = []
    if hasattr(type(obj), "aliases"):
        aliases = [a.value for a in obj.aliases.all()]
    return {
        "name": obj.name,
        "slug": obj.slug,
        "display_order": obj.display_order,
        "description": _build_rich_text(
            obj, "description", getattr(obj, "active_claims", [])
        ),
        "aliases": aliases,
        "sources": build_sources(getattr(obj, "active_claims", [])),
    }


def _list_taxonomy_with_counts(
    model_class, mm_relation: str, *, sort_by_display_order: bool = False
) -> list[dict]:
    """Standard list response for flat (non-DAG) model-attached taxonomies.

    Default sort is title_count desc (popular first). Pass
    ``sort_by_display_order=True`` for small, chronologically-meaningful
    taxonomies (tech generations, game formats) where editorial order is
    more useful to users than popularity.
    """
    items = list(
        model_class.objects.active().prefetch_related(
            *(["aliases"] if hasattr(model_class, "aliases") else [])
        )
    )
    counts = bulk_title_counts_via_models([t.pk for t in items], mm_relation)
    if sort_by_display_order:
        items.sort(key=lambda t: (t.display_order, t.name.lower()))
    else:
        items.sort(key=lambda t: (-counts.get(t.pk, 0), t.name.lower()))
    return [
        {**_serialize_taxonomy(t), "title_count": counts.get(t.pk, 0)} for t in items
    ]


def _taxonomy_detail_qs(model_class):
    prefetches = [claims_prefetch()]
    if hasattr(model_class, "aliases"):
        prefetches.append("aliases")
    return model_class.objects.active().prefetch_related(*prefetches)


def _patch_taxonomy(request, model_class, slug, data):
    """Shared PATCH handler for all taxonomy entities."""
    obj = get_object_or_404(model_class.objects.active(), slug=slug)
    specs = plan_scalar_field_claims(model_class, data.fields, entity=obj)

    execute_claims(
        obj, specs, user=request.user, note=data.note, citation=data.citation
    )

    obj = get_object_or_404(_taxonomy_detail_qs(model_class), slug=obj.slug)
    return _serialize_taxonomy(obj)


def _register_delete_restore(router: Router, model_cls, **kwargs) -> None:
    """Thin wrapper — auto-plumbs the standard taxonomy detail/serialize pair."""
    register_entity_delete_restore(
        router,
        model_cls,
        detail_qs=lambda cls=model_cls: _taxonomy_detail_qs(cls),
        serialize_detail=_serialize_taxonomy,
        response_schema=TaxonomySchema,
        **kwargs,
    )


def _register_create(router: Router, model_cls, **kwargs) -> None:
    register_entity_create(
        router,
        model_cls,
        detail_qs=lambda cls=model_cls: _taxonomy_detail_qs(cls),
        serialize_detail=_serialize_taxonomy,
        response_schema=TaxonomySchema,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Technology Generations router
# ---------------------------------------------------------------------------

technology_generations_router = Router(tags=["technology-generations"])


@technology_generations_router.get("/", response=list[TaxonomyWithTitleCountSchema])
@decorate_view(cache_control(no_cache=True))
def list_technology_generations(request):
    return _list_taxonomy_with_counts(
        TechnologyGeneration, "technology_generation", sort_by_display_order=True
    )


@technology_generations_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_technology_generation(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, TechnologyGeneration, slug, data)


# ---------------------------------------------------------------------------
# Display Types router
# ---------------------------------------------------------------------------

display_types_router = Router(tags=["display-types"])


@display_types_router.get("/", response=list[DisplayTypeListSchema])
@decorate_view(cache_control(no_cache=True))
def list_display_types(request):
    types = list(DisplayType.objects.active())
    subtypes = list(DisplaySubtype.objects.active())

    type_counts = bulk_title_counts_via_models([t.pk for t in types], "display_type")
    subtype_counts = bulk_title_counts_via_models(
        [s.pk for s in subtypes], "display_subtype"
    )

    subtypes_by_type: dict[int, list[DisplaySubtype]] = {}
    for s in subtypes:
        subtypes_by_type.setdefault(s.display_type_id, []).append(s)
    for group in subtypes_by_type.values():
        group.sort(key=lambda s: (s.display_order, s.name.lower()))

    types.sort(key=lambda t: (t.display_order, t.name.lower()))

    return [
        {
            **_serialize_taxonomy(t),
            "title_count": type_counts.get(t.pk, 0),
            "subtypes": [
                {
                    **_serialize_taxonomy(s),
                    "title_count": subtype_counts.get(s.pk, 0),
                }
                for s in subtypes_by_type.get(t.pk, [])
            ],
        }
        for t in types
    ]


@display_types_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_display_type(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, DisplayType, slug, data)


# ---------------------------------------------------------------------------
# Technology Subgenerations router
# ---------------------------------------------------------------------------

technology_subgenerations_router = Router(tags=["technology-subgenerations"])


@technology_subgenerations_router.get("/", response=list[TaxonomyWithTitleCountSchema])
@decorate_view(cache_control(no_cache=True))
def list_technology_subgenerations(request):
    return _list_taxonomy_with_counts(
        TechnologySubgeneration,
        "technology_subgeneration",
        sort_by_display_order=True,
    )


@technology_subgenerations_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_technology_subgeneration(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, TechnologySubgeneration, slug, data)


# ---------------------------------------------------------------------------
# Display Subtypes router
# ---------------------------------------------------------------------------

display_subtypes_router = Router(tags=["display-subtypes"])


@display_subtypes_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_display_subtype(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, DisplaySubtype, slug, data)


# ---------------------------------------------------------------------------
# Cabinets router
# ---------------------------------------------------------------------------

cabinets_router = Router(tags=["cabinets"])


@cabinets_router.get("/", response=list[TaxonomyWithTitleCountSchema])
@decorate_view(cache_control(no_cache=True))
def list_cabinets(request):
    return _list_taxonomy_with_counts(Cabinet, "cabinet")


@cabinets_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_cabinet(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, Cabinet, slug, data)


# ---------------------------------------------------------------------------
# Game Formats router
# ---------------------------------------------------------------------------

game_formats_router = Router(tags=["game-formats"])


@game_formats_router.get("/", response=list[TaxonomyWithTitleCountSchema])
@decorate_view(cache_control(no_cache=True))
def list_game_formats(request):
    return _list_taxonomy_with_counts(
        GameFormat, "game_format", sort_by_display_order=True
    )


@game_formats_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_game_format(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, GameFormat, slug, data)


# ---------------------------------------------------------------------------
# Reward Types router
# ---------------------------------------------------------------------------


class RewardTypeDetailSchema(TaxonomySchema):
    machines: list[TitleMachineSchema] = []


reward_types_router = Router(tags=["reward-types"])


def _reward_type_detail_qs():
    return RewardType.objects.active().prefetch_related(
        claims_prefetch(),
        Prefetch(
            "machine_models",
            queryset=MachineModel.objects.active()
            .filter(variant_of__isnull=True)
            .select_related("corporate_entity__manufacturer", "technology_generation")
            .order_by(F("year").desc(nulls_last=True), "name"),
        ),
    )


def _serialize_reward_type_detail(rt) -> dict:
    min_rank = get_minimum_display_rank()
    return {
        **_serialize_taxonomy(rt),
        "machines": [
            _serialize_title_machine(pm, min_rank=min_rank)
            for pm in rt.machine_models.all()
        ],
    }


@reward_types_router.get("/", response=list[TaxonomyWithTitleCountSchema])
@decorate_view(cache_control(no_cache=True))
def list_reward_types(request):
    return _list_taxonomy_with_counts(RewardType, "reward_types")


@reward_types_router.patch(
    "/{slug}/claims/",
    auth=django_auth,
    response=RewardTypeDetailSchema,
    tags=["private"],
)
def patch_reward_type(request, slug: str, data: ClaimPatchSchema):
    obj = get_object_or_404(RewardType.objects.active(), slug=slug)
    specs = plan_scalar_field_claims(RewardType, data.fields, entity=obj)

    execute_claims(
        obj, specs, user=request.user, note=data.note, citation=data.citation
    )

    rt = get_object_or_404(_reward_type_detail_qs(), slug=obj.slug)
    return _serialize_reward_type_detail(rt)


# ---------------------------------------------------------------------------
# Tags router
# ---------------------------------------------------------------------------

tags_router = Router(tags=["tags"])


@tags_router.get("/", response=list[TaxonomyWithTitleCountSchema])
@decorate_view(cache_control(no_cache=True))
def list_tags(request):
    return _list_taxonomy_with_counts(Tag, "tags")


@tags_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_tag(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, Tag, slug, data)


# ---------------------------------------------------------------------------
# Credit Roles router
# ---------------------------------------------------------------------------

credit_roles_router = Router(tags=["credit-roles"])


@credit_roles_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_credit_roles(request):
    return [
        _serialize_taxonomy(c) for c in CreditRole.objects.active().order_by("name")
    ]


@credit_roles_router.get("/{slug}", response=TaxonomySchema)
@decorate_view(cache_control(no_cache=True))
def get_credit_role(request, slug: str):
    return _serialize_taxonomy(
        get_object_or_404(_taxonomy_detail_qs(CreditRole), slug=slug)
    )


# ---------------------------------------------------------------------------
# Create / delete / restore wiring
# ---------------------------------------------------------------------------

# Delete / restore / preview — every target entity on its own router.
_register_delete_restore(
    technology_generations_router,
    TechnologyGeneration,
    child_related_name="subgenerations",
)
_register_delete_restore(
    technology_subgenerations_router,
    TechnologySubgeneration,
    parent_field="technology_generation",
)
_register_delete_restore(
    display_types_router,
    DisplayType,
    child_related_name="subtypes",
)
_register_delete_restore(
    display_subtypes_router,
    DisplaySubtype,
    parent_field="display_type",
)
_register_delete_restore(cabinets_router, Cabinet)
_register_delete_restore(game_formats_router, GameFormat)
_register_delete_restore(tags_router, Tag)
_register_delete_restore(reward_types_router, RewardType)

# Create — parentless entities on their own router.
_register_create(technology_generations_router, TechnologyGeneration)
_register_create(display_types_router, DisplayType)
_register_create(cabinets_router, Cabinet)
_register_create(game_formats_router, GameFormat)
_register_create(tags_router, Tag)
_register_create(reward_types_router, RewardType)

# Create — parented entities nested under the parent's router.
_register_create(
    technology_generations_router,
    TechnologySubgeneration,
    parent_field="technology_generation",
    parent_model=TechnologyGeneration,
    route_suffix="subgenerations",
)
_register_create(
    display_types_router,
    DisplaySubtype,
    parent_field="display_type",
    parent_model=DisplayType,
    route_suffix="subtypes",
)
