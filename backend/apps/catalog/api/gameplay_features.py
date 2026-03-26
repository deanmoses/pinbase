"""Gameplay features router — list, detail, and claims endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_control
from ninja import Router, Schema
from ninja.decorators import decorate_view
from ninja.errors import HttpError
from ninja.security import django_auth

from .helpers import _build_activity, _build_rich_text, _claims_prefetch
from .schemas import (
    ClaimSchema,
    GameplayFeatureClaimPatchSchema,
    GameplayFeatureSchema,
    RichTextSchema,
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class GameplayFeatureListSchema(Schema):
    name: str
    slug: str
    model_count: int = 0
    parent_slugs: list[str] = []


class GameplayFeatureDetailSchema(Schema):
    name: str
    slug: str
    description: RichTextSchema = RichTextSchema()
    aliases: list[str] = []
    parents: list[GameplayFeatureSchema] = []
    children: list[GameplayFeatureSchema] = []
    activity: list[ClaimSchema] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detail_qs():
    from ..models import GameplayFeature

    return GameplayFeature.objects.prefetch_related(
        "parents", "children", "aliases", _claims_prefetch()
    )


def _normalize(s: str) -> str:
    s = s.lower().replace("-", "").replace(" ", "")
    if s.endswith("s"):
        s = s[:-1]
    return s


def _serialize_detail(feature) -> dict:
    canonical_norm = _normalize(feature.name)
    display_aliases = [
        a.value for a in feature.aliases.all() if _normalize(a.value) != canonical_norm
    ]
    return {
        "name": feature.name,
        "slug": feature.slug,
        "description": _build_rich_text(
            feature, "description", getattr(feature, "active_claims", [])
        ),
        "aliases": display_aliases,
        "parents": [{"name": p.name, "slug": p.slug} for p in feature.parents.all()],
        "children": [
            {"name": c.name, "slug": c.slug} for c in feature.children.order_by("name")
        ],
        "activity": _build_activity(getattr(feature, "active_claims", [])),
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

gameplay_features_router = Router(tags=["gameplay-features"])


@gameplay_features_router.get("/", response=list[GameplayFeatureListSchema])
@decorate_view(cache_control(public=True, max_age=300))
def list_gameplay_features(request):
    from ..models import GameplayFeature, MachineModel

    features = list(
        GameplayFeature.objects.prefetch_related("children", "parents").order_by("name")
    )

    # Build children map for transitive closure.
    children_map: dict[int, list[int]] = {
        f.pk: [c.pk for c in f.children.all()] for f in features
    }

    # Fetch (gameplay_feature_pk, machinemodel_pk) for non-variant machines only.
    Through = MachineModel.gameplay_features.through
    feature_to_model_pks: dict[int, set[int]] = {}
    for gf_pk, mm_pk in Through.objects.filter(
        machinemodel__variant_of__isnull=True
    ).values_list("gameplayfeature_id", "machinemodel_id"):
        feature_to_model_pks.setdefault(gf_pk, set()).add(mm_pk)

    def _get_descendants(pk: int) -> set[int]:
        result: set[int] = {pk}
        stack = [pk]
        while stack:
            current = stack.pop()
            for child_pk in children_map.get(current, []):
                if child_pk not in result:
                    result.add(child_pk)
                    stack.append(child_pk)
        return result

    result = []
    for f in features:
        descendants = _get_descendants(f.pk)
        all_model_pks: set[int] = set()
        for d_pk in descendants:
            all_model_pks |= feature_to_model_pks.get(d_pk, set())
        result.append(
            {
                "name": f.name,
                "slug": f.slug,
                "model_count": len(all_model_pks),
                "parent_slugs": [p.slug for p in f.parents.all()],
            }
        )
    return result


@gameplay_features_router.get("/{slug}", response=GameplayFeatureDetailSchema)
@decorate_view(cache_control(public=True, max_age=300))
def get_gameplay_feature(request, slug: str):
    feature = get_object_or_404(_detail_qs(), slug=slug)
    return _serialize_detail(feature)


@dataclass(frozen=True)
class _ClaimSpec:
    """A planned claim to be written — separates diffing from execution."""

    field_name: str
    value: object
    claim_key: str = ""


def _validate_and_plan_claims(
    feature,
    data: GameplayFeatureClaimPatchSchema,
) -> tuple[list[_ClaimSpec], bool]:
    """Validate input and return (claim_specs, parents_changed).

    Scalar fields are assertion-based: a spec is created for every field in
    the request, even if the value matches the current state. Reasserting
    the same value is meaningful (e.g., a user confirming a machine-sourced
    value). The frontend is responsible for only sending changed fields.

    Parent relationships are diff-based: specs are only created for parents
    that are actually being added or removed relative to the current M2M
    state, because redundant ``exists=True`` claims are pure waste.

    Raises HttpError on validation failure or if no specs would be created.
    """
    from apps.catalog.claims import build_relationship_claim
    from apps.core.markdown_links import prepare_markdown_claim_value
    from apps.core.models import get_claim_fields

    from ..models import GameplayFeature

    specs: list[_ClaimSpec] = []

    # --- Scalars ---
    editable_fields = set(get_claim_fields(GameplayFeature))
    unknown = set(data.fields.keys()) - editable_fields
    if unknown:
        raise HttpError(422, f"Unknown or non-editable fields: {sorted(unknown)}")

    for field_name, value in data.fields.items():
        try:
            value = prepare_markdown_claim_value(field_name, value, GameplayFeature)
        except ValidationError as exc:
            raise HttpError(422, "; ".join(exc.messages)) from exc
        specs.append(_ClaimSpec(field_name=field_name, value=value))

    # --- Parents ---
    parents_changed = False
    if data.parents is not None:
        desired = set(data.parents)

        if feature.slug in desired:
            raise HttpError(422, "A feature cannot be its own parent.")

        existing_slugs = set(
            GameplayFeature.objects.filter(slug__in=desired).values_list(
                "slug", flat=True
            )
        )
        missing = desired - existing_slugs
        if missing:
            raise HttpError(422, f"Unknown parent slugs: {sorted(missing)}")

        # Cycle detection
        if desired:
            all_features = GameplayFeature.objects.prefetch_related("parents").all()
            parent_map: dict[str, set[str]] = {}
            for f in all_features:
                if f.slug == feature.slug:
                    continue
                parent_map[f.slug] = {p.slug for p in f.parents.all()}

            for start_slug in desired:
                visited: set[str] = set()
                stack = [start_slug]
                while stack:
                    current = stack.pop()
                    if current == feature.slug:
                        raise HttpError(
                            422,
                            f"Adding parent '{start_slug}' would create a cycle.",
                        )
                    if current in visited:
                        continue
                    visited.add(current)
                    stack.extend(parent_map.get(current, set()))

        # Diff against current M2M state
        current = set(feature.parents.values_list("slug", flat=True))
        for parent_slug in desired - current:
            claim_key, value = build_relationship_claim(
                "gameplay_feature_parent", {"parent_slug": parent_slug}
            )
            specs.append(
                _ClaimSpec(
                    field_name="gameplay_feature_parent",
                    value=value,
                    claim_key=claim_key,
                )
            )
        for parent_slug in current - desired:
            claim_key, value = build_relationship_claim(
                "gameplay_feature_parent", {"parent_slug": parent_slug}, exists=False
            )
            specs.append(
                _ClaimSpec(
                    field_name="gameplay_feature_parent",
                    value=value,
                    claim_key=claim_key,
                )
            )
        parents_changed = bool((desired - current) or (current - desired))

    if not specs:
        raise HttpError(422, "No changes provided.")

    return specs, parents_changed


def _execute_claims(feature, specs, parents_changed, user, note):
    """Create a ChangeSet + claims atomically and resolve."""
    from django.db import transaction

    from apps.provenance.models import ChangeSet, Claim

    from ..resolve import resolve_entity
    from ..resolve._relationships import resolve_gameplay_feature_parents

    with transaction.atomic():
        cs = ChangeSet.objects.create(user=user, note=note)
        for spec in specs:
            Claim.objects.assert_claim(
                feature,
                spec.field_name,
                spec.value,
                user=user,
                claim_key=spec.claim_key,
                changeset=cs,
            )
        if parents_changed:
            resolve_gameplay_feature_parents()
        resolve_entity(feature)


@gameplay_features_router.patch(
    "/{slug}/claims/",
    auth=django_auth,
    response=GameplayFeatureDetailSchema,
    tags=["private"],
)
def patch_gameplay_feature_claims(
    request, slug: str, data: GameplayFeatureClaimPatchSchema
):
    """Assert per-field claims from the authenticated user, then re-resolve."""
    from ..cache import invalidate_all
    from ..models import GameplayFeature

    if not data.fields and data.parents is None:
        raise HttpError(422, "No changes provided.")

    feature = get_object_or_404(GameplayFeature, slug=slug)

    specs, parents_changed = _validate_and_plan_claims(feature, data)

    try:
        _execute_claims(feature, specs, parents_changed, request.user, data.note)
    except IntegrityError as exc:
        raise HttpError(422, f"Unique constraint violation: {exc}") from exc

    invalidate_all()

    feature = get_object_or_404(_detail_qs(), slug=feature.slug)
    return _serialize_detail(feature)
