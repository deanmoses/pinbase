"""Claim → MachineModel resolution logic.

Given a MachineModel, fetch all active claims, pick the winner per field
(highest source priority, most recent if tied), and write back the resolved
values.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import models
from django.db.models import Case, F, IntegerField, Value, When
from django.utils import timezone

from apps.provenance.models import Claim

from .models import MachineGroup, MachineModel, Manufacturer, ManufacturerEntity, Person

logger = logging.getLogger(__name__)

# Fields on MachineModel that can be set directly from a claim value.
# Maps field_name (as stored in Claim.field_name) → model attribute name.
DIRECT_FIELDS: dict[str, str] = {
    "name": "name",
    "year": "year",
    "month": "month",
    "machine_type": "machine_type",
    "display_type": "display_type",
    "player_count": "player_count",
    "theme": "theme",
    "production_quantity": "production_quantity",
    "mpu": "mpu",
    "flipper_count": "flipper_count",
    "ipdb_rating": "ipdb_rating",
    "pinside_rating": "pinside_rating",
    "educational_text": "educational_text",
    "sources_notes": "sources_notes",
    "ipdb_id": "ipdb_id",
    "opdb_id": "opdb_id",
    "pinside_id": "pinside_id",
}

# Fields that should be coerced to int (nullable).
_INT_FIELDS = {
    "year",
    "month",
    "player_count",
    "flipper_count",
    "ipdb_id",
    "pinside_id",
}

# Fields that should be coerced to Decimal (nullable).
_DECIMAL_FIELDS = {"ipdb_rating", "pinside_rating"}


def _coerce(field_name: str, value):
    """Coerce a JSON claim value to the type expected by the model field."""
    if value is None or value == "":
        return None

    if field_name in _INT_FIELDS:
        try:
            return int(value)
        except ValueError, TypeError:
            logger.warning("Cannot coerce %r to int for field %s", value, field_name)
            return None

    if field_name in _DECIMAL_FIELDS:
        try:
            return Decimal(str(value))
        except InvalidOperation, ValueError, TypeError:
            logger.warning(
                "Cannot coerce %r to Decimal for field %s", value, field_name
            )
            return None

    return value


def _resolve_group(value) -> MachineGroup | None:
    """Resolve a group claim value to a MachineGroup instance.

    The value is expected to be an OPDB group ID string (e.g., "G5pe4").
    """
    if value is None or value == "":
        return None
    group = MachineGroup.objects.filter(opdb_id=str(value)).first()
    if not group:
        logger.warning("Unmatched group claim value: %r", value)
    return group


def _resolve_manufacturer(value, source_slug: str = "") -> Manufacturer | None:
    """Resolve a manufacturer claim value to a Manufacturer instance.

    The value can be:
    - An int/string matching ipdb_manufacturer_id (on ManufacturerEntity)
      or opdb_manufacturer_id (on Manufacturer)
    - A manufacturer name string

    ``source_slug`` disambiguates numeric IDs: "ipdb" looks up via
    ManufacturerEntity, "opdb" via Manufacturer.opdb_manufacturer_id.
    Without a slug, both are tried (IPDB first, then OPDB).
    """
    if value is None or value == "":
        return None

    # Try numeric ID lookups, scoped by source when known.
    try:
        numeric_id = int(value)

        if source_slug != "opdb":
            entity = (
                ManufacturerEntity.objects.filter(ipdb_manufacturer_id=numeric_id)
                .select_related("manufacturer")
                .first()
            )
            if entity:
                return entity.manufacturer

        if source_slug != "ipdb":
            mfr = Manufacturer.objects.filter(opdb_manufacturer_id=numeric_id).first()
            if mfr:
                return mfr
    except ValueError, TypeError:
        pass

    # Fall back to name match (case-insensitive).
    name = str(value).strip()
    if not name:
        return None

    mfr = Manufacturer.objects.filter(name__iexact=name).first()
    if mfr:
        return mfr

    mfr = Manufacturer.objects.filter(trade_name__iexact=name).first()
    if mfr:
        return mfr

    logger.warning("Unmatched manufacturer claim value: %r", value)
    return None


def resolve_model(machine_model: MachineModel) -> MachineModel:
    """Resolve all active claims into the given MachineModel's fields.

    Picks the winning claim per field_name: highest effective priority
    (from source or user profile), then most recent created_at as tiebreaker.

    Returns the saved MachineModel.
    """
    claims = (
        machine_model.claims.filter(is_active=True)
        .select_related("source", "user__profile")
        .annotate(
            effective_priority=Case(
                When(source__isnull=False, then=F("source__priority")),
                When(user__isnull=False, then=F("user__profile__priority")),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("field_name", "-effective_priority", "-created_at")
    )

    # Group by field_name — first claim per group is the winner.
    winners: dict[str, Claim] = {}
    for claim in claims:
        if claim.field_name not in winners:
            winners[claim.field_name] = claim

    # Reset all resolvable fields to defaults before applying winners.
    # This ensures deactivated claims don't leave stale values.
    machine_model.manufacturer = None
    machine_model.group = None
    for attr in DIRECT_FIELDS.values():
        field = machine_model._meta.get_field(attr)
        if hasattr(field, "default") and field.default is not models.NOT_PROVIDED:
            setattr(machine_model, attr, field.default)
        elif field.null:
            setattr(machine_model, attr, None)
        else:
            setattr(machine_model, attr, "")
    extra_data: dict = {}

    # Apply winners to the model.
    for field_name, claim in winners.items():
        if field_name == "manufacturer":
            machine_model.manufacturer = _resolve_manufacturer(
                claim.value, source_slug=claim.source.slug if claim.source else ""
            )
        elif field_name == "group":
            machine_model.group = _resolve_group(claim.value)
        elif field_name in DIRECT_FIELDS:
            attr = DIRECT_FIELDS[field_name]
            setattr(machine_model, attr, _coerce(field_name, claim.value))
        else:
            # Goes into extra_data catch-all.
            extra_data[field_name] = claim.value

    machine_model.extra_data = extra_data

    # Guard against UNIQUE constraint on opdb_id: if another model already
    # owns this opdb_id, clear it rather than crashing.
    if machine_model.opdb_id:
        conflict = (
            MachineModel.objects.filter(opdb_id=machine_model.opdb_id)
            .exclude(pk=machine_model.pk)
            .first()
        )
        if conflict:
            logger.warning(
                "Cannot resolve opdb_id=%s onto '%s' (pk=%s): "
                "already owned by '%s' (pk=%s)",
                machine_model.opdb_id,
                machine_model.name,
                machine_model.pk,
                conflict.name,
                conflict.pk,
            )
            machine_model.opdb_id = None

    machine_model.save()
    return machine_model


def resolve_all() -> int:
    """Re-resolve every MachineModel from its claims (bulk-optimized).

    Pre-fetches all lookup tables and claims in ~4 queries, resolves
    in memory, then writes back with a single bulk_update().
    """
    # 1. Pre-fetch lookup tables (~3 queries).
    mfr_lookups = _build_manufacturer_lookups()
    group_lookup = _build_group_lookup()
    field_defaults = _get_field_defaults()

    # 2. Pre-fetch all active claims, grouped by object_id (~1 query).
    claims_by_model = _build_claims_by_model()

    # 3. Load all MachineModels (~1 query).
    all_models = list(MachineModel.objects.all())

    # 4. Resolve each model in memory.
    for pm in all_models:
        winners = claims_by_model.get(pm.pk, {})
        _apply_resolution(pm, winners, field_defaults, mfr_lookups, group_lookup)

    # 5. Detect opdb_id conflicts across all resolved models.
    _resolve_opdb_conflicts(all_models)

    # 6. Set updated_at (auto_now not triggered by bulk_update).
    now = timezone.now()
    for pm in all_models:
        pm.updated_at = now

    # 7. Bulk write (~1 query, batched).
    update_fields = list(DIRECT_FIELDS.values()) + [
        "manufacturer_id",
        "group_id",
        "extra_data",
        "updated_at",
    ]
    # batch_size=100 is optimal for SQLite (CASE WHEN overhead grows with
    # batch size × field count). PostgreSQL uses a more efficient UPDATE FROM
    # VALUES syntax and handles larger batches fine.
    MachineModel.objects.bulk_update(all_models, update_fields, batch_size=100)

    return len(all_models)


# ------------------------------------------------------------------
# Bulk resolution helpers (used by resolve_all)
# ------------------------------------------------------------------

_field_defaults: dict[str, Any] | None = None


def _get_field_defaults() -> dict[str, Any]:
    """Compute reset values for all DIRECT_FIELDS (cached after first call)."""
    global _field_defaults
    if _field_defaults is not None:
        return _field_defaults
    defaults: dict[str, Any] = {}
    for attr in DIRECT_FIELDS.values():
        field = MachineModel._meta.get_field(attr)
        if hasattr(field, "default") and field.default is not models.NOT_PROVIDED:
            defaults[attr] = (
                field.default() if callable(field.default) else field.default
            )
        elif field.null:
            defaults[attr] = None
        else:
            defaults[attr] = ""
    _field_defaults = defaults
    return _field_defaults


def _build_manufacturer_lookups() -> tuple[
    dict[int, Manufacturer],
    dict[int, Manufacturer],
    dict[str, Manufacturer],
    dict[str, Manufacturer],
]:
    """Pre-fetch all manufacturer data into four lookup dicts."""
    ipdb_id_to_mfr: dict[int, Manufacturer] = {}
    for entity in ManufacturerEntity.objects.select_related("manufacturer").all():
        if entity.ipdb_manufacturer_id is not None:
            ipdb_id_to_mfr[entity.ipdb_manufacturer_id] = entity.manufacturer

    opdb_id_to_mfr: dict[int, Manufacturer] = {}
    name_to_mfr: dict[str, Manufacturer] = {}
    trade_name_to_mfr: dict[str, Manufacturer] = {}
    for mfr in Manufacturer.objects.all():
        if mfr.opdb_manufacturer_id is not None:
            opdb_id_to_mfr[mfr.opdb_manufacturer_id] = mfr
        if mfr.name:
            name_to_mfr[mfr.name.lower()] = mfr
        if mfr.trade_name:
            trade_name_to_mfr[mfr.trade_name.lower()] = mfr

    return ipdb_id_to_mfr, opdb_id_to_mfr, name_to_mfr, trade_name_to_mfr


def _build_group_lookup() -> dict[str, MachineGroup]:
    """Pre-fetch all groups into {opdb_id: MachineGroup}."""
    return {g.opdb_id: g for g in MachineGroup.objects.all()}


def _build_claims_by_model() -> dict[int, dict[str, Claim]]:
    """Pre-fetch all active claims for MachineModel, pick winner per (object_id, field_name).

    Returns {object_id: {field_name: winning_claim}}.
    """
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(MachineModel)
    claims = (
        Claim.objects.filter(is_active=True, content_type=ct)
        .select_related("source", "user__profile")
        .annotate(
            effective_priority=Case(
                When(source__isnull=False, then=F("source__priority")),
                When(user__isnull=False, then=F("user__profile__priority")),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("object_id", "field_name", "-effective_priority", "-created_at")
    )

    result: dict[int, dict[str, Claim]] = {}
    for claim in claims:
        model_winners = result.setdefault(claim.object_id, {})
        # First claim per (object_id, field_name) group is the winner.
        if claim.field_name not in model_winners:
            model_winners[claim.field_name] = claim

    return result


def _resolve_manufacturer_bulk(
    value,
    source_slug: str,
    mfr_lookups: tuple[
        dict[int, Manufacturer],
        dict[int, Manufacturer],
        dict[str, Manufacturer],
        dict[str, Manufacturer],
    ],
) -> Manufacturer | None:
    """Same logic as _resolve_manufacturer() but uses pre-fetched dicts."""
    if value is None or value == "":
        return None

    ipdb_id_to_mfr, opdb_id_to_mfr, name_to_mfr, trade_name_to_mfr = mfr_lookups

    try:
        numeric_id = int(value)

        if source_slug != "opdb":
            mfr = ipdb_id_to_mfr.get(numeric_id)
            if mfr:
                return mfr

        if source_slug != "ipdb":
            mfr = opdb_id_to_mfr.get(numeric_id)
            if mfr:
                return mfr
    except ValueError, TypeError:
        pass

    name = str(value).strip()
    if not name:
        return None

    mfr = name_to_mfr.get(name.lower())
    if mfr:
        return mfr

    mfr = trade_name_to_mfr.get(name.lower())
    if mfr:
        return mfr

    logger.warning("Unmatched manufacturer claim value: %r", value)
    return None


def _resolve_group_bulk(
    value, group_lookup: dict[str, MachineGroup]
) -> MachineGroup | None:
    """Same logic as _resolve_group() but uses pre-fetched dict."""
    if value is None or value == "":
        return None
    group = group_lookup.get(str(value))
    if not group:
        logger.warning("Unmatched group claim value: %r", value)
    return group


def _apply_resolution(
    pm: MachineModel,
    winners: dict[str, Claim],
    field_defaults: dict[str, Any],
    mfr_lookups: tuple,
    group_lookup: dict[str, MachineGroup],
) -> None:
    """Apply claim winners to a MachineModel instance in memory."""
    # Reset FK fields.
    pm.manufacturer = None
    pm.group = None

    # Reset all DIRECT_FIELDS to defaults.
    for attr, default in field_defaults.items():
        setattr(pm, attr, default)

    # Fresh extra_data dict (never shared between models).
    extra_data: dict = {}

    # Apply winners.
    for field_name, claim in winners.items():
        if field_name == "manufacturer":
            pm.manufacturer = _resolve_manufacturer_bulk(
                claim.value,
                source_slug=claim.source.slug if claim.source else "",
                mfr_lookups=mfr_lookups,
            )
        elif field_name == "group":
            pm.group = _resolve_group_bulk(claim.value, group_lookup)
        elif field_name in DIRECT_FIELDS:
            attr = DIRECT_FIELDS[field_name]
            setattr(pm, attr, _coerce(field_name, claim.value))
        else:
            extra_data[field_name] = claim.value

    pm.extra_data = extra_data


MANUFACTURER_DIRECT_FIELDS: dict[str, str] = {
    "name": "name",
    "trade_name": "trade_name",
    "description": "description",
    "founded_year": "founded_year",
    "dissolved_year": "dissolved_year",
    "country": "country",
    "headquarters": "headquarters",
    "logo_url": "logo_url",
    "website": "website",
}

_MANUFACTURER_INT_FIELDS: frozenset[str] = frozenset({"founded_year", "dissolved_year"})

PERSON_DIRECT_FIELDS: dict[str, str] = {
    "name": "name",
    "bio": "bio",
    "birth_year": "birth_year",
    "birth_month": "birth_month",
    "birth_day": "birth_day",
    "death_year": "death_year",
    "death_month": "death_month",
    "death_day": "death_day",
    "birth_place": "birth_place",
    "nationality": "nationality",
    "photo_url": "photo_url",
}

_PERSON_INT_FIELDS: frozenset[str] = frozenset(
    {
        "birth_year",
        "birth_month",
        "birth_day",
        "death_year",
        "death_month",
        "death_day",
    }
)


def _resolve_simple(
    obj,
    direct_fields: dict[str, str],
    int_fields: frozenset[str] | None = None,
) -> None:
    """Resolve active claims onto an object with only direct fields.

    All resolvable fields are reset to their defaults first, then active
    claim winners are applied.  Claims are the sole source of truth for
    these fields: a field with no active claim will be blank/null after
    resolution regardless of what was previously stored.

    Mutates *obj* in memory; the caller is responsible for saving.
    Pass *int_fields* to coerce matching claim values to ``int``.
    """
    claims = (
        obj.claims.filter(is_active=True)
        .select_related("source", "user__profile")
        .annotate(
            effective_priority=Case(
                When(source__isnull=False, then=F("source__priority")),
                When(user__isnull=False, then=F("user__profile__priority")),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("field_name", "-effective_priority", "-created_at")
    )

    winners: dict[str, Claim] = {}
    for claim in claims:
        if claim.field_name not in winners:
            winners[claim.field_name] = claim

    # Reset resolvable fields to defaults.
    for attr in direct_fields.values():
        field = obj._meta.get_field(attr)
        if hasattr(field, "default") and field.default is not models.NOT_PROVIDED:
            setattr(obj, attr, field.default)
        elif field.null:
            setattr(obj, attr, None)
        else:
            setattr(obj, attr, "")

    # Apply winners.
    for field_name, claim in winners.items():
        if field_name in direct_fields:
            attr = direct_fields[field_name]
            value = claim.value
            if int_fields and field_name in int_fields:
                setattr(obj, attr, None if value is None else int(value))
            else:
                setattr(obj, attr, "" if value is None else value)


def resolve_manufacturer(mfr: Manufacturer) -> Manufacturer:
    """Resolve active claims into the given Manufacturer's fields.

    Returns the saved Manufacturer.
    """
    _resolve_simple(
        mfr, MANUFACTURER_DIRECT_FIELDS, int_fields=_MANUFACTURER_INT_FIELDS
    )
    mfr.save()
    return mfr


def resolve_person(person: Person) -> Person:
    """Resolve active claims into the given Person's fields.

    Returns the saved Person.
    """
    _resolve_simple(person, PERSON_DIRECT_FIELDS, int_fields=_PERSON_INT_FIELDS)
    person.save()
    return person


def _resolve_opdb_conflicts(all_models: list[MachineModel]) -> None:
    """Clear opdb_id on models that would cause UNIQUE constraint violations.

    First model encountered (by queryset order) wins ownership.
    """
    seen_opdb_ids: dict[str, MachineModel] = {}
    for pm in all_models:
        if not pm.opdb_id:
            continue
        if pm.opdb_id in seen_opdb_ids:
            owner = seen_opdb_ids[pm.opdb_id]
            logger.warning(
                "Cannot resolve opdb_id=%s onto '%s' (pk=%s): "
                "already owned by '%s' (pk=%s)",
                pm.opdb_id,
                pm.name,
                pm.pk,
                owner.name,
                owner.pk,
            )
            pm.opdb_id = None
        else:
            seen_opdb_ids[pm.opdb_id] = pm
