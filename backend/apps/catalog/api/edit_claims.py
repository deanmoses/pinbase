"""Shared helpers for PATCH claims endpoints.

Provides the plan/execute pattern for entity editing: validate input,
build a list of ClaimSpecs, then execute them atomically in a ChangeSet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from ninja.errors import HttpError

from ..cache import invalidate_all


@dataclass(frozen=True)
class ClaimSpec:
    """A planned claim to be written — separates diffing from execution."""

    field_name: str
    value: object
    claim_key: str = ""


def plan_scalar_field_claims(
    model_class, fields: dict, *, entity=None
) -> list[ClaimSpec]:
    """Validate scalar fields and reject empty/no-op field payloads.

    Shared by PATCH endpoints that only accept scalar ``fields`` payloads.
    """
    if not fields:
        raise HttpError(422, "No changes provided.")

    specs = validate_scalar_fields(model_class, fields, entity=entity)
    if not specs:
        raise HttpError(422, "No changes provided.")
    return specs


def get_field_constraints(model_class) -> dict[str, dict]:
    """Extract min/max/step constraints from numeric claim fields.

    Returns a dict like ``{"year": {"min": 1800, "max": 2100, "step": 1}}``.
    Only fields with at least one validator-derived constraint are included.
    Step is derived from ``DecimalField.decimal_places``.
    """
    from django.core.validators import MaxValueValidator, MinValueValidator
    from django.db import models as db_models

    from apps.core.models import get_claim_fields

    numeric_types = (
        db_models.IntegerField,
        db_models.SmallIntegerField,
        db_models.PositiveIntegerField,
        db_models.PositiveSmallIntegerField,
        db_models.DecimalField,
        db_models.FloatField,
    )
    editable = get_claim_fields(model_class)
    constraints: dict[str, dict] = {}

    for field_name in editable:
        field = model_class._meta.get_field(field_name)
        if not isinstance(field, numeric_types):
            continue

        entry: dict[str, float | int] = {}
        # Use _validators (explicitly declared) rather than .validators
        # (which includes DB-range validators like max=9223372036854775807).
        for v in field._validators:
            if isinstance(v, MinValueValidator):
                entry["min"] = v.limit_value
            elif isinstance(v, MaxValueValidator):
                entry["max"] = v.limit_value

        if not entry:
            continue
        if isinstance(field, db_models.DecimalField) and field.decimal_places:
            entry["step"] = float(f"1e-{field.decimal_places}")
        else:
            entry["step"] = 1
        constraints[field_name] = entry

    return constraints


def validate_scalar_fields(
    model_class, fields: dict, *, entity=None
) -> list[ClaimSpec]:
    """Validate scalar fields and return ClaimSpecs.

    Scalar fields are assertion-based: a spec is created for every field in
    the request, even if the value matches the current state. Reasserting
    the same value is meaningful (e.g., a user confirming a machine-sourced
    value). The frontend is responsible for only sending changed fields.

    Raises HttpError 422 on unknown fields or invalid markdown.
    """
    from apps.core.models import get_claim_fields
    from apps.provenance.validation import validate_claim_value

    editable = set(get_claim_fields(model_class))
    unknown = set(fields.keys()) - editable
    if unknown:
        raise HttpError(422, f"Unknown or non-editable fields: {sorted(unknown)}")

    specs: list[ClaimSpec] = []
    for field_name, value in fields.items():
        field = model_class._meta.get_field(field_name)
        # Claim.value is NOT NULL; store allowed clears as "" and let the
        # resolver coerce that sentinel back to None/blank based on field
        # metadata. Required fields must reject clears up front.
        if value is None:
            if not (field.null or getattr(field, "blank", False)):
                raise HttpError(422, f"Field '{field_name}' cannot be cleared.")
            value = ""
        try:
            value = validate_claim_value(field_name, value, model_class)
        except ValidationError as exc:
            raise HttpError(422, "; ".join(exc.messages)) from exc
        if getattr(field, "unique", False) and value != "":
            conflict_qs = model_class.objects.filter(**{field_name: value})
            if entity is not None and getattr(entity, "pk", None) is not None:
                conflict_qs = conflict_qs.exclude(pk=entity.pk)
            if conflict_qs.exists():
                raise HttpError(422, f"Field '{field_name}' must be unique.")
        specs.append(ClaimSpec(field_name=field_name, value=value))
    return specs


def plan_parent_claims(
    entity,
    desired_slugs: set[str],
    *,
    model_class,
    claim_field_name: str,
) -> list[ClaimSpec]:
    """Validate parent hierarchy changes and return diff-based ClaimSpecs.

    Works for any model with a self-referencing ``parents`` M2M resolved
    via relationship claims (GameplayFeature, Theme).

    Raises HttpError 422 on invalid slugs, self-links, or cycles.
    """
    from apps.catalog.claims import build_relationship_claim

    if entity.slug in desired_slugs:
        raise HttpError(422, f"A {model_class.__name__} cannot be its own parent.")

    existing = set(
        model_class.objects.filter(slug__in=desired_slugs).values_list(
            "slug", flat=True
        )
    )
    missing = desired_slugs - existing
    if missing:
        raise HttpError(422, f"Unknown parent slugs: {sorted(missing)}")

    # Cycle detection: for each proposed parent, walk up the existing
    # graph (excluding the edited entity's current parents, since
    # they're being replaced). If we reach the edited entity, reject.
    if desired_slugs:
        all_entities = model_class.objects.prefetch_related("parents").all()
        parent_map: dict[str, set[str]] = {}
        for e in all_entities:
            if e.slug == entity.slug:
                continue
            parent_map[e.slug] = {p.slug for p in e.parents.all()}

        for start_slug in desired_slugs:
            visited: set[str] = set()
            stack = [start_slug]
            while stack:
                current = stack.pop()
                if current == entity.slug:
                    raise HttpError(
                        422,
                        f"Adding parent '{start_slug}' would create a cycle.",
                    )
                if current in visited:
                    continue
                visited.add(current)
                stack.extend(parent_map.get(current, set()))

    # Diff against current M2M state
    current_slugs = set(entity.parents.values_list("slug", flat=True))
    specs: list[ClaimSpec] = []
    for parent_slug in desired_slugs - current_slugs:
        claim_key, value = build_relationship_claim(
            claim_field_name, {"parent_slug": parent_slug}
        )
        specs.append(
            ClaimSpec(field_name=claim_field_name, value=value, claim_key=claim_key)
        )
    for parent_slug in current_slugs - desired_slugs:
        claim_key, value = build_relationship_claim(
            claim_field_name, {"parent_slug": parent_slug}, exists=False
        )
        specs.append(
            ClaimSpec(field_name=claim_field_name, value=value, claim_key=claim_key)
        )
    return specs


def plan_alias_claims(
    entity,
    desired_aliases: list[str],
    *,
    claim_field_name: str,
) -> list[ClaimSpec]:
    """Validate alias changes and return diff-based ClaimSpecs.

    Normalises input (strip, deduplicate by lowercase key) and diffs
    against current alias rows.  Preserves user-typed case via
    ``alias_display`` so the resolver stores the display form.

    Returns specs for adds, removes, and display-case updates.
    """
    from apps.catalog.claims import build_relationship_claim

    # Normalise: strip, deduplicate by lowercase key, drop blanks.
    # Last-write-wins for display case when duplicates differ only in case.
    desired: dict[str, str] = {}  # lowercase → display string
    for raw in desired_aliases:
        val = raw.strip()
        if val:
            desired[val.lower()] = val

    current: dict[str, str] = {}  # lowercase → stored display string
    for a in entity.aliases.all():
        current[a.value.lower()] = a.value

    specs: list[ClaimSpec] = []
    # Adds and display-case updates
    for lower, display in desired.items():
        if lower not in current or current[lower] != display:
            claim_key, value = build_relationship_claim(
                claim_field_name,
                {"alias_value": lower, "alias_display": display},
            )
            specs.append(
                ClaimSpec(field_name=claim_field_name, value=value, claim_key=claim_key)
            )
    # Removes
    for lower in current.keys() - desired.keys():
        claim_key, value = build_relationship_claim(
            claim_field_name, {"alias_value": lower}, exists=False
        )
        specs.append(
            ClaimSpec(field_name=claim_field_name, value=value, claim_key=claim_key)
        )
    return specs


def plan_m2m_claims(
    entity,
    desired_slugs: set[str],
    *,
    target_model,
    claim_field_name: str,
    slug_key: str,
    m2m_attr: str,
) -> list[ClaimSpec]:
    """Validate and diff a simple slug-set M2M relationship.

    Works for any MachineModel M2M that is resolved by slug (themes, tags,
    reward_types).  Unlike ``plan_parent_claims``, no hierarchy or cycle
    checks are needed.

    Raises HttpError 422 on unknown slugs.
    """
    if desired_slugs:
        existing = set(
            target_model.objects.filter(slug__in=desired_slugs).values_list(
                "slug", flat=True
            )
        )
        desired = normalize_slug_set_inputs(
            desired_slugs,
            available_slugs=existing,
            error_label=claim_field_name,
        )
    else:
        desired = normalize_slug_set_inputs(desired_slugs, error_label=claim_field_name)

    current_slugs = {obj.slug for obj in getattr(entity, m2m_attr).all()}
    return build_m2m_claim_specs(
        current=current_slugs,
        desired=desired,
        claim_field_name=claim_field_name,
        slug_key=slug_key,
    )


def normalize_slug_set_inputs(
    desired_slugs: set[str],
    *,
    available_slugs: set[str] | None = None,
    error_label: str,
) -> set[str]:
    """Validate a slug-set relationship input against optional available slugs."""
    if available_slugs is not None:
        missing = desired_slugs - available_slugs
        if missing:
            raise HttpError(422, f"Unknown {error_label} slugs: {sorted(missing)}")
    return desired_slugs


def build_m2m_claim_specs(
    *,
    current: set[str],
    desired: set[str],
    claim_field_name: str,
    slug_key: str,
) -> list[ClaimSpec]:
    """Build diff-based ClaimSpecs for simple slug-set M2M relationships."""
    from apps.catalog.claims import build_relationship_claim

    specs: list[ClaimSpec] = []
    for slug in desired - current:
        claim_key, value = build_relationship_claim(claim_field_name, {slug_key: slug})
        specs.append(
            ClaimSpec(field_name=claim_field_name, value=value, claim_key=claim_key)
        )
    for slug in current - desired:
        claim_key, value = build_relationship_claim(
            claim_field_name, {slug_key: slug}, exists=False
        )
        specs.append(
            ClaimSpec(field_name=claim_field_name, value=value, claim_key=claim_key)
        )
    return specs


def normalize_gameplay_feature_inputs(
    desired_features: list[tuple[str, int | None]],
    *,
    available_slugs: set[str] | None = None,
) -> dict[str, int | None]:
    """Normalize gameplay feature input into a slug->count map.

    Duplicate slugs are rejected. Counts, when provided, must be positive.
    When ``available_slugs`` is provided, unknown slugs are rejected without
    touching the database.
    """
    desired: dict[str, int | None] = {}
    for slug, count in desired_features:
        if slug in desired:
            raise HttpError(422, f"Duplicate gameplay feature slug: {slug!r}")
        if count is not None and count <= 0:
            raise HttpError(422, f"Count must be positive for {slug!r}, got {count}")
        desired[slug] = count

    if available_slugs is not None:
        missing = set(desired.keys()) - available_slugs
        if missing:
            raise HttpError(422, f"Unknown gameplay_feature slugs: {sorted(missing)}")

    return desired


def build_gameplay_feature_claim_specs(
    current: dict[str, int | None],
    desired: dict[str, int | None],
) -> list[ClaimSpec]:
    """Build diff-based ClaimSpecs for gameplay feature relationship changes."""
    from apps.catalog.claims import build_relationship_claim

    specs: list[ClaimSpec] = []
    for slug, count in desired.items():
        if slug not in current or current[slug] != count:
            claim_key, value = build_relationship_claim(
                "gameplay_feature", {"gameplay_feature_slug": slug}
            )
            value["count"] = count
            specs.append(
                ClaimSpec(
                    field_name="gameplay_feature",
                    value=value,
                    claim_key=claim_key,
                )
            )
    for slug in current.keys() - desired.keys():
        claim_key, value = build_relationship_claim(
            "gameplay_feature", {"gameplay_feature_slug": slug}, exists=False
        )
        specs.append(
            ClaimSpec(
                field_name="gameplay_feature",
                value=value,
                claim_key=claim_key,
            )
        )
    return specs


def plan_gameplay_feature_claims(
    entity,
    desired_features: list,
) -> list[ClaimSpec]:
    """Validate and diff gameplay features (slug + optional count) on a MachineModel.

    Each entry has a ``slug`` and optional ``count``.  Duplicate slugs in the
    input are rejected.  Count must be positive if provided.

    Assumes ``entity`` has a ``machinemodelgameplayfeature_set`` reverse
    relation (i.e., is a MachineModel with that through-table prefetched).

    Raises HttpError 422 on invalid input.
    """
    from apps.catalog.models import GameplayFeature

    raw_desired = [(feat.slug, feat.count) for feat in desired_features]
    if raw_desired:
        existing = set(
            GameplayFeature.objects.filter(
                slug__in={slug for slug, _ in raw_desired}
            ).values_list("slug", flat=True)
        )
        desired = normalize_gameplay_feature_inputs(
            raw_desired, available_slugs=existing
        )
    else:
        desired = normalize_gameplay_feature_inputs(raw_desired)

    # Current state from prefetched through-table.
    current: dict[str, int | None] = {}
    for row in entity.machinemodelgameplayfeature_set.all():
        current[row.gameplayfeature.slug] = row.count

    return build_gameplay_feature_claim_specs(current, desired)


def plan_abbreviation_claims(
    entity,
    desired_values: list[str],
) -> list[ClaimSpec]:
    """Validate and diff abbreviation changes.

    Normalises input (strip, deduplicate, drop blanks, enforce max length)
    and diffs against current abbreviation rows.

    Shared by MachineModel and Title.
    """
    from apps.catalog.claims import build_relationship_claim

    desired = set(_normalize_abbreviations(desired_values))
    current = set(entity.abbreviations.values_list("value", flat=True))
    specs: list[ClaimSpec] = []

    for value in desired - current:
        claim_key, claim_value = build_relationship_claim(
            "abbreviation", {"value": value}
        )
        specs.append(
            ClaimSpec(field_name="abbreviation", value=claim_value, claim_key=claim_key)
        )

    for value in current - desired:
        claim_key, claim_value = build_relationship_claim(
            "abbreviation", {"value": value}, exists=False
        )
        specs.append(
            ClaimSpec(field_name="abbreviation", value=claim_value, claim_key=claim_key)
        )
    return specs


def plan_credit_claims(
    entity,
    desired_credits: list,
) -> list[ClaimSpec]:
    """Validate and diff credits (person_slug + role) on a MachineModel.

    Each entry has a ``person_slug`` and ``role`` (role slug).  Duplicate
    (person_slug, role) pairs in the input are rejected.

    Assumes ``entity`` has ``credits`` prefetched with
    select_related("person", "role").

    Raises HttpError 422 on invalid input.
    """
    from apps.catalog.models import CreditRole, Person

    raw_desired = [(credit.person_slug, credit.role) for credit in desired_credits]

    if raw_desired:
        desired_person_slugs = {p for p, _ in raw_desired}
        existing_people = set(
            Person.objects.filter(slug__in=desired_person_slugs).values_list(
                "slug", flat=True
            )
        )
        desired_role_slugs = {r for _, r in raw_desired}
        existing_roles = set(
            CreditRole.objects.filter(slug__in=desired_role_slugs).values_list(
                "slug", flat=True
            )
        )
        desired = normalize_credit_inputs(
            raw_desired,
            available_people=existing_people,
            available_roles=existing_roles,
        )
    else:
        desired = normalize_credit_inputs(raw_desired)

    # Current state from prefetched credits.
    current: set[tuple[str, str]] = set()
    for credit in entity.credits.all():
        current.add((credit.person.slug, credit.role.slug))

    return build_credit_claim_specs(current, desired)


def normalize_credit_inputs(
    desired_credits: list[tuple[str, str]],
    *,
    available_people: set[str] | None = None,
    available_roles: set[str] | None = None,
) -> set[tuple[str, str]]:
    """Normalize credits into unique (person_slug, role_slug) pairs.

    When available slug sets are provided, unknown people or roles are rejected
    without touching the database.
    """
    desired: set[tuple[str, str]] = set()
    for person_slug, role in desired_credits:
        pair = (person_slug, role)
        if pair in desired:
            raise HttpError(
                422,
                f"Duplicate credit: person={person_slug!r}, role={role!r}",
            )
        desired.add(pair)

    if available_people is not None:
        missing_people = {p for p, _ in desired} - available_people
        if missing_people:
            raise HttpError(422, f"Unknown person slugs: {sorted(missing_people)}")

    if available_roles is not None:
        missing_roles = {r for _, r in desired} - available_roles
        if missing_roles:
            raise HttpError(422, f"Unknown credit role slugs: {sorted(missing_roles)}")

    return desired


def build_credit_claim_specs(
    current: set[tuple[str, str]],
    desired: set[tuple[str, str]],
) -> list[ClaimSpec]:
    """Build diff-based ClaimSpecs for credit relationship changes."""
    from apps.catalog.claims import build_relationship_claim

    specs: list[ClaimSpec] = []
    for person_slug, role in desired - current:
        claim_key, value = build_relationship_claim(
            "credit", {"person_slug": person_slug, "role": role}
        )
        specs.append(ClaimSpec(field_name="credit", value=value, claim_key=claim_key))
    for person_slug, role in current - desired:
        claim_key, value = build_relationship_claim(
            "credit", {"person_slug": person_slug, "role": role}, exists=False
        )
        specs.append(ClaimSpec(field_name="credit", value=value, claim_key=claim_key))
    return specs


def _normalize_abbreviations(values: list[str]) -> list[str]:
    """Strip, deduplicate, drop blanks, enforce max length."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = raw_value.strip()
        if not value:
            continue
        if len(value) > 50:
            raise HttpError(422, "Abbreviations must be 50 characters or fewer.")
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def execute_claims(
    entity,
    specs: list[ClaimSpec],
    *,
    user,
    note: str = "",
    resolvers: list[Callable] | None = None,
    resolve_fn: Callable | None = None,
) -> None:
    """Create a ChangeSet + claims atomically, resolve, and invalidate cache.

    ``resolvers`` is an optional list of callables to run inside the
    transaction before the entity resolver — e.g., relationship resolvers
    like ``resolve_gameplay_feature_parents``.

    ``resolve_fn`` overrides the default ``resolve_entity`` — used by
    MachineModel which needs ``resolve_model`` instead.

    Raises HttpError 422 on IntegrityError (unique constraint violations).
    """
    from apps.provenance.models import ChangeSet, Claim

    if resolve_fn is None:
        from ..resolve import resolve_entity

        resolve_fn = resolve_entity

    try:
        with transaction.atomic():
            cs = ChangeSet.objects.create(user=user, note=note)
            for spec in specs:
                Claim.objects.assert_claim(
                    entity,
                    spec.field_name,
                    spec.value,
                    user=user,
                    claim_key=spec.claim_key,
                    changeset=cs,
                )
            for resolver in resolvers or []:
                resolver()
            resolve_fn(entity)
    except IntegrityError as exc:
        raise HttpError(422, f"Unique constraint violation: {exc}") from exc

    invalidate_all()
