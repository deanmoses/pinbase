"""Taxonomy routers — technology generations, display types, and related lookups."""

from __future__ import annotations

from typing import Optional

from django.db.models import F, Prefetch
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view
from ninja.responses import Status
from ninja.security import django_auth

from apps.catalog.naming import normalize_catalog_name
from apps.provenance.helpers import build_sources, claims_prefetch
from apps.provenance.models import ChangeSetAction
from apps.provenance.rate_limits import (
    CREATE_RATE_LIMIT_SPEC,
    DELETE_RATE_LIMIT_SPEC,
    check_and_record,
)

from .edit_claims import ClaimSpec, execute_claims, plan_scalar_field_claims
from .entity_create import (
    assert_name_available,
    assert_slug_available,
    create_entity_with_claims,
    validate_name,
    validate_slug_format,
)
from .soft_delete import (
    SoftDeleteBlocked,
    count_entity_changesets,
    execute_soft_delete,
    plan_soft_delete,
    serialize_blocking_referrer,
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
    BlockingReferrerSchema,
    ClaimPatchSchema,
    ClaimSchema,
    EditCitationInput,
    RichTextSchema,
    TitleMachineSchema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_taxonomy(obj) -> dict:
    return {
        "name": obj.name,
        "slug": obj.slug,
        "display_order": obj.display_order,
        "description": _build_rich_text(
            obj, "description", getattr(obj, "active_claims", [])
        ),
        "sources": build_sources(getattr(obj, "active_claims", [])),
    }


def _taxonomy_detail_qs(model_class):
    return model_class.objects.active().prefetch_related(claims_prefetch())


def _patch_taxonomy(request, model_class, slug, data):
    """Shared PATCH handler for all taxonomy entities."""
    obj = get_object_or_404(model_class.objects.active(), slug=slug)
    specs = plan_scalar_field_claims(model_class, data.fields, entity=obj)

    execute_claims(
        obj, specs, user=request.user, note=data.note, citation=data.citation
    )

    obj = get_object_or_404(_taxonomy_detail_qs(model_class), slug=obj.slug)
    return _serialize_taxonomy(obj)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TaxonomySchema(Schema):
    name: str
    slug: str
    display_order: int
    description: RichTextSchema = RichTextSchema()
    sources: list[ClaimSchema] = []


class TaxonomyCreateSchema(Schema):
    name: str
    slug: str
    note: str = ""
    citation: EditCitationInput | None = None


class TaxonomyDeleteSchema(Schema):
    note: str = ""
    citation: EditCitationInput | None = None


class TaxonomyRestoreSchema(Schema):
    note: str = ""
    citation: EditCitationInput | None = None


class TaxonomyDeletePreviewSchema(Schema):
    name: str
    slug: str
    changeset_count: int
    blocked_by: list[BlockingReferrerSchema] = []
    # 0 on leaf entities; non-zero only for parents (tech-gen, display-type)
    # whose active children would block the delete.
    active_children_count: int = 0
    # Populated on subgen/subtype so the UI can show a parent breadcrumb.
    parent_name: Optional[str] = None
    parent_slug: Optional[str] = None


class TaxonomyDeleteResponseSchema(Schema):
    """Success body for taxonomy soft-delete.

    ``affected_slugs`` is always ``[obj.slug]`` — taxonomy deletes block
    rather than cascade — but the list shape keeps parity with
    ``ModelDeleteResponseSchema.affected_models`` (which can be >1 for the
    Title cascade) so the frontend delete helper can be shared.
    """

    changeset_id: int
    affected_slugs: list[str]


# ---------------------------------------------------------------------------
# Shared create / delete / restore helpers
# ---------------------------------------------------------------------------


def _register_taxonomy_delete_restore(
    router: Router,
    model_cls,
    *,
    child_related_name: str | None = None,
    parent_field: str | None = None,
) -> None:
    """Attach delete-preview, delete, and restore routes to *router*.

    * ``child_related_name`` — set on entities with active-child blocking
      (tech-gen → subgenerations, display-type → subtypes). The accessor
      name is the ``related_name=`` declared on the child FK, not the
      model's ``_meta.default_manager``.
    * ``parent_field`` — set on subgen/subtype so the preview response can
      surface the parent's name/slug, and restore can refuse when the
      parent is currently soft-deleted.
    """
    entity_label = model_cls.__name__
    friendly = model_cls.entity_type.replace("-", " ")
    friendly_sentence = friendly.capitalize()

    def _delete_preview(request, slug: str):
        obj = get_object_or_404(model_cls.objects.active(), slug=slug)
        plan = plan_soft_delete(obj)

        active_children = 0
        if child_related_name is not None:
            active_children = getattr(obj, child_related_name).active().count()

        is_blocked = plan.is_blocked or active_children > 0
        changeset_count = 0 if is_blocked else count_entity_changesets(obj)

        parent_name: str | None = None
        parent_slug: str | None = None
        if parent_field is not None:
            parent = getattr(obj, parent_field)
            parent_name = parent.name
            parent_slug = parent.slug

        return {
            "name": obj.name,
            "slug": obj.slug,
            "changeset_count": changeset_count,
            "blocked_by": [serialize_blocking_referrer(b) for b in plan.blockers],
            "active_children_count": active_children,
            "parent_name": parent_name,
            "parent_slug": parent_slug,
        }

    _delete_preview.__name__ = f"{entity_label.lower()}_delete_preview"
    router.get(
        "/{slug}/delete-preview/",
        auth=django_auth,
        response=TaxonomyDeletePreviewSchema,
        tags=["private"],
    )(_delete_preview)

    def _delete(request, slug: str, data: TaxonomyDeleteSchema):
        check_and_record(request.user, DELETE_RATE_LIMIT_SPEC)

        obj = get_object_or_404(model_cls.objects.active(), slug=slug)

        if child_related_name is not None:
            active_children = getattr(obj, child_related_name).active().count()
            if active_children > 0:
                # The empty ``blocked_by`` array is required — the shared
                # frontend classifier in delete-flow.ts only treats a 422
                # as a ``blocked`` outcome when ``blocked_by`` is present
                # as an array; otherwise it falls through to a generic
                # form error and loses the structured state.
                return Status(
                    422,
                    {
                        "detail": (
                            f"Cannot delete: {obj.name} has {active_children} "
                            f"active child"
                            f"{'ren' if active_children != 1 else ''}. "
                            "Delete those first."
                        ),
                        "blocked_by": [],
                        "active_children_count": active_children,
                    },
                )

        try:
            changeset, deleted = execute_soft_delete(
                obj, user=request.user, note=data.note, citation=data.citation
            )
        except SoftDeleteBlocked as exc:
            return Status(
                422,
                {
                    "detail": (
                        "Cannot delete: active references would be left dangling."
                    ),
                    "blocked_by": [
                        serialize_blocking_referrer(b) for b in exc.blockers
                    ],
                    "active_children_count": 0,
                },
            )

        if changeset is None:
            return Status(422, {"detail": f"{friendly_sentence} is already deleted."})

        return {
            "changeset_id": changeset.pk,
            "affected_slugs": [e.slug for e in deleted if isinstance(e, model_cls)],
        }

    _delete.__name__ = f"{entity_label.lower()}_delete"
    router.post(
        "/{slug}/delete/",
        auth=django_auth,
        response={200: TaxonomyDeleteResponseSchema, 422: dict},
        tags=["private"],
    )(_delete)

    def _restore(request, slug: str, data: TaxonomyRestoreSchema):
        check_and_record(request.user, CREATE_RATE_LIMIT_SPEC)

        # Bypass .active() — we're looking for soft-deleted rows.
        obj = get_object_or_404(model_cls, slug=slug)
        if obj.status != "deleted":
            return Status(422, {"detail": f"{friendly_sentence} is not deleted."})

        if parent_field is not None:
            parent = getattr(obj, parent_field)
            if parent.status == "deleted":
                return Status(
                    422,
                    {"detail": f"Restore {parent.name} first."},
                )

        execute_claims(
            obj,
            [ClaimSpec(field_name="status", value="active")],
            user=request.user,
            action=ChangeSetAction.EDIT,
            note=data.note,
            citation=data.citation,
        )

        refreshed = get_object_or_404(_taxonomy_detail_qs(model_cls), slug=slug)
        return _serialize_taxonomy(refreshed)

    _restore.__name__ = f"{entity_label.lower()}_restore"
    router.post(
        "/{slug}/restore/",
        auth=django_auth,
        response={200: TaxonomySchema, 422: dict, 404: dict},
        tags=["private"],
    )(_restore)


def _register_taxonomy_create(
    router: Router,
    model_cls,
    *,
    parent_field: str | None = None,
    parent_model=None,
    route_suffix: str = "",
) -> None:
    """Attach a POST create route.

    When *parent_field* is None, mounts ``POST /`` on the entity's own
    router. Otherwise all three parent-related args must be supplied
    together and the route mounts at ``POST /{parent_slug}/<route_suffix>/``
    on the *parent's* router — mirroring the Title → Model nesting.

    *parent_field* is passed explicitly (e.g. ``parent_field="technology_generation"``)
    rather than introspected from the FK — keeps call sites declarative.

    FK claim values are stored as the parent's slug string, matching the
    shipped convention (see titles.py:1091 and the ``claim_fk_lookups``
    contract validated at provenance/validation.py:286).
    """
    parented = parent_field is not None
    if parented and not (parent_model and route_suffix):
        raise TypeError(
            "_register_taxonomy_create: when parent_field is set, "
            "parent_model and route_suffix are required."
        )

    entity_label = model_cls.__name__
    name_max = model_cls._meta.get_field("name").max_length
    friendly = model_cls.entity_type.replace("-", " ")

    def _do_create(request, data: TaxonomyCreateSchema, parent=None):
        check_and_record(request.user, CREATE_RATE_LIMIT_SPEC)

        name = validate_name(data.name, max_length=name_max)
        slug = validate_slug_format(data.slug)
        assert_name_available(
            model_cls,
            name,
            normalize=normalize_catalog_name,
            friendly_label=friendly,
        )
        assert_slug_available(model_cls, slug)

        row_kwargs: dict = {"name": name, "slug": slug, "status": "active"}
        claim_specs = [
            ClaimSpec(field_name="name", value=name),
            ClaimSpec(field_name="slug", value=slug),
            ClaimSpec(field_name="status", value="active"),
        ]
        if parent is not None:
            row_kwargs[parent_field] = parent
            # FK claim value is the parent's slug string.
            claim_specs.append(ClaimSpec(field_name=parent_field, value=parent.slug))

        create_entity_with_claims(
            model_cls,
            row_kwargs=row_kwargs,
            claim_specs=claim_specs,
            user=request.user,
            note=data.note,
            citation=data.citation,
        )

        created = get_object_or_404(_taxonomy_detail_qs(model_cls), slug=slug)
        return Status(201, _serialize_taxonomy(created))

    if parented:

        def _create(request, parent_slug: str, data: TaxonomyCreateSchema):
            parent = get_object_or_404(parent_model.objects.active(), slug=parent_slug)
            return _do_create(request, data, parent=parent)

        path = f"/{{parent_slug}}/{route_suffix}/"
    else:

        def _create(request, data: TaxonomyCreateSchema):
            return _do_create(request, data)

        path = "/"

    _create.__name__ = f"{entity_label.lower()}_create"
    router.post(
        path,
        auth=django_auth,
        response={201: TaxonomySchema},
        tags=["private"],
    )(_create)


# ---------------------------------------------------------------------------
# Technology Generations router
# ---------------------------------------------------------------------------

technology_generations_router = Router(tags=["technology-generations"])


@technology_generations_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_technology_generations(request):
    return [
        _serialize_taxonomy(t)
        for t in TechnologyGeneration.objects.active().order_by("display_order")
    ]


@technology_generations_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_technology_generation(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, TechnologyGeneration, slug, data)


# ---------------------------------------------------------------------------
# Display Types router
# ---------------------------------------------------------------------------

display_types_router = Router(tags=["display-types"])


@display_types_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_display_types(request):
    return [
        _serialize_taxonomy(d)
        for d in DisplayType.objects.active().order_by("display_order")
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


@technology_subgenerations_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_technology_subgenerations(request):
    return [
        _serialize_taxonomy(t)
        for t in TechnologySubgeneration.objects.active().order_by("display_order")
    ]


@technology_subgenerations_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_technology_subgeneration(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, TechnologySubgeneration, slug, data)


# ---------------------------------------------------------------------------
# Display Subtypes router
# ---------------------------------------------------------------------------

display_subtypes_router = Router(tags=["display-subtypes"])


@display_subtypes_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_display_subtypes(request):
    return [
        _serialize_taxonomy(d)
        for d in DisplaySubtype.objects.active().order_by("display_order")
    ]


@display_subtypes_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_display_subtype(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, DisplaySubtype, slug, data)


# ---------------------------------------------------------------------------
# Cabinets router
# ---------------------------------------------------------------------------

cabinets_router = Router(tags=["cabinets"])


@cabinets_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_cabinets(request):
    return [
        _serialize_taxonomy(c)
        for c in Cabinet.objects.active().order_by("display_order")
    ]


@cabinets_router.patch(
    "/{slug}/claims/", auth=django_auth, response=TaxonomySchema, tags=["private"]
)
def patch_cabinet(request, slug: str, data: ClaimPatchSchema):
    return _patch_taxonomy(request, Cabinet, slug, data)


# ---------------------------------------------------------------------------
# Game Formats router
# ---------------------------------------------------------------------------

game_formats_router = Router(tags=["game-formats"])


@game_formats_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_game_formats(request):
    return [
        _serialize_taxonomy(g)
        for g in GameFormat.objects.active().order_by("display_order")
    ]


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


@reward_types_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_reward_types(request):
    return [
        _serialize_taxonomy(rt)
        for rt in RewardType.objects.active().order_by("display_order", "name")
    ]


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


@tags_router.get("/", response=list[TaxonomySchema])
@decorate_view(cache_control(no_cache=True))
def list_tags(request):
    return [
        _serialize_taxonomy(t) for t in Tag.objects.active().order_by("display_order")
    ]


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
        _serialize_taxonomy(c)
        for c in CreditRole.objects.active().order_by("display_order")
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
_register_taxonomy_delete_restore(
    technology_generations_router,
    TechnologyGeneration,
    child_related_name="subgenerations",
)
_register_taxonomy_delete_restore(
    technology_subgenerations_router,
    TechnologySubgeneration,
    parent_field="technology_generation",
)
_register_taxonomy_delete_restore(
    display_types_router,
    DisplayType,
    child_related_name="subtypes",
)
_register_taxonomy_delete_restore(
    display_subtypes_router,
    DisplaySubtype,
    parent_field="display_type",
)
_register_taxonomy_delete_restore(cabinets_router, Cabinet)
_register_taxonomy_delete_restore(game_formats_router, GameFormat)
_register_taxonomy_delete_restore(tags_router, Tag)
_register_taxonomy_delete_restore(reward_types_router, RewardType)

# Create — parentless entities on their own router.
_register_taxonomy_create(technology_generations_router, TechnologyGeneration)
_register_taxonomy_create(display_types_router, DisplayType)
_register_taxonomy_create(cabinets_router, Cabinet)
_register_taxonomy_create(game_formats_router, GameFormat)
_register_taxonomy_create(tags_router, Tag)
_register_taxonomy_create(reward_types_router, RewardType)

# Create — parented entities nested under the parent's router.
_register_taxonomy_create(
    technology_generations_router,
    TechnologySubgeneration,
    parent_field="technology_generation",
    parent_model=TechnologyGeneration,
    route_suffix="subgenerations",
)
_register_taxonomy_create(
    display_types_router,
    DisplaySubtype,
    parent_field="display_type",
    parent_model=DisplayType,
    route_suffix="subtypes",
)
