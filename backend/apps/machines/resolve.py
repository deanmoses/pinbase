"""Claim → PinballModel resolution logic.

Given a PinballModel, fetch all active claims, pick the winner per field
(highest source priority, most recent if tied), and write back the resolved
values.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.db import models
from django.db.models import F

from .models import Claim, Manufacturer, PinballModel

logger = logging.getLogger(__name__)

# Fields on PinballModel that can be set directly from a claim value.
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


def _resolve_manufacturer(value) -> Manufacturer | None:
    """Resolve a manufacturer claim value to a Manufacturer instance.

    The value can be:
    - An int/string matching ipdb_manufacturer_id or opdb_manufacturer_id
    - A manufacturer name string
    """
    if value is None or value == "":
        return None

    # Try numeric ID lookups first.
    try:
        numeric_id = int(value)
        mfr = Manufacturer.objects.filter(ipdb_manufacturer_id=numeric_id).first()
        if mfr:
            return mfr
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


def resolve_model(pinball_model: PinballModel) -> PinballModel:
    """Resolve all active claims into the given PinballModel's fields.

    Picks the winning claim per field_name: highest source priority,
    then most recent created_at as tiebreaker.

    Returns the saved PinballModel.
    """
    claims = (
        Claim.objects.filter(model=pinball_model, is_active=True)
        .annotate(source_priority=F("source__priority"))
        .order_by("field_name", "-source_priority", "-created_at")
    )

    # Group by field_name — first claim per group is the winner.
    winners: dict[str, Claim] = {}
    for claim in claims:
        if claim.field_name not in winners:
            winners[claim.field_name] = claim

    # Reset all resolvable fields to defaults before applying winners.
    # This ensures deactivated claims don't leave stale values.
    pinball_model.manufacturer = None
    for attr in DIRECT_FIELDS.values():
        field = pinball_model._meta.get_field(attr)
        if hasattr(field, "default") and field.default is not models.NOT_PROVIDED:
            setattr(pinball_model, attr, field.default)
        elif field.null:
            setattr(pinball_model, attr, None)
        else:
            setattr(pinball_model, attr, "")
    extra_data: dict = {}

    # Apply winners to the model.
    for field_name, claim in winners.items():
        if field_name == "manufacturer":
            pinball_model.manufacturer = _resolve_manufacturer(claim.value)
        elif field_name in DIRECT_FIELDS:
            attr = DIRECT_FIELDS[field_name]
            setattr(pinball_model, attr, _coerce(field_name, claim.value))
        else:
            # Goes into extra_data catch-all.
            extra_data[field_name] = claim.value

    pinball_model.extra_data = extra_data
    pinball_model.save()
    return pinball_model


def resolve_all() -> int:
    """Re-resolve every PinballModel from its claims. Returns count resolved."""
    count = 0
    for pm in PinballModel.objects.all():
        resolve_model(pm)
        count += 1
    return count
