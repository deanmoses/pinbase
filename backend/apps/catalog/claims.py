"""Catalog-level helpers for relationship claims.

Domain knowledge about relationship claim types lives here, keeping the
provenance layer fully generic.  Ingestion commands and the resolution layer
import from this module rather than constructing claim_keys directly.
"""

from __future__ import annotations

from typing import NamedTuple

from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.provenance.models import make_claim_key

# ---------------------------------------------------------------------------
# Relationship schema registry
# ---------------------------------------------------------------------------
# Two kinds of relationship namespace:
#
# Entity-reference — value dict keys are PKs referencing target models.
#   ENTITY_REF_TARGETS is the single source of truth: schema keys,
#   validation target registration, and RELATIONSHIP_NAMESPACES are all
#   derived from it.
#
# Literal-value — value dict keys store literal strings (aliases,
#   abbreviations) where value_key differs from identity_key.


class RefKey(NamedTuple):
    """An entity-reference key in a relationship claim value dict."""

    name: str  # key in both value dict and claim_key ("person", "theme")
    model: type[models.Model]  # target model for PK validation


class LiteralKey(NamedTuple):
    """A literal-value key where the value dict key differs from the claim_key key."""

    value_key: str  # key in claim value dict ("alias_value")
    identity_key: str  # key in claim_key string ("alias")


def _build_entity_ref_targets() -> dict[str, list[RefKey]]:
    """Deferred import to avoid circular dependency at module load."""
    from apps.catalog.models import (
        CreditRole,
        GameplayFeature,
        Location,
        Person,
        RewardType,
        Tag,
        Theme,
        Title,
    )

    return {
        "credit": [RefKey("person", Person), RefKey("role", CreditRole)],
        "theme": [RefKey("theme", Theme)],
        "tag": [RefKey("tag", Tag)],
        "gameplay_feature": [RefKey("gameplay_feature", GameplayFeature)],
        "reward_type": [RefKey("reward_type", RewardType)],
        "location": [RefKey("location", Location)],
        "theme_parent": [RefKey("parent", Theme)],
        "gameplay_feature_parent": [RefKey("parent", GameplayFeature)],
        "series_title": [RefKey("title", Title)],
    }


# Populated lazily by _get_entity_ref_targets().
_entity_ref_targets: dict[str, list[RefKey]] | None = None


def _get_entity_ref_targets() -> dict[str, list[RefKey]]:
    global _entity_ref_targets  # noqa: PLW0603
    if _entity_ref_targets is None:
        _entity_ref_targets = _build_entity_ref_targets()
    return _entity_ref_targets


LITERAL_SCHEMAS: dict[str, LiteralKey] = {
    "abbreviation": LiteralKey("value", "value"),
    "theme_alias": LiteralKey("alias_value", "alias"),
    "manufacturer_alias": LiteralKey("alias_value", "alias"),
    "person_alias": LiteralKey("alias_value", "alias"),
    "gameplay_feature_alias": LiteralKey("alias_value", "alias"),
    "reward_type_alias": LiteralKey("alias_value", "alias"),
    "corporate_entity_alias": LiteralKey("alias_value", "alias"),
    "location_alias": LiteralKey("alias_value", "alias"),
}

# Eagerly computable — literal namespace names are string constants.
_LITERAL_NAMESPACES = frozenset(LITERAL_SCHEMAS)


_relationship_namespaces: frozenset[str] | None = None


def get_relationship_namespaces() -> frozenset[str]:
    """Return the full set of relationship namespace names.

    Lazy — safe to call at any time; caches after first call.
    """
    global _relationship_namespaces  # noqa: PLW0603
    if _relationship_namespaces is None:
        _relationship_namespaces = (
            frozenset(_get_entity_ref_targets()) | _LITERAL_NAMESPACES
        )
    return _relationship_namespaces


def register_relationship_targets() -> None:
    """Push catalog target-model knowledge into the provenance registry.

    Called once from ``CatalogConfig.ready()``.  Derived from
    ``ENTITY_REF_TARGETS`` — no hand-maintained second dict.
    """
    from apps.provenance.validation import register_relationship_targets as _register

    _register(
        {
            namespace: [(rk.name, rk.model, "pk") for rk in ref_keys]
            for namespace, ref_keys in _get_entity_ref_targets().items()
        }
    )


# ---------------------------------------------------------------------------
# Claim construction helpers
# ---------------------------------------------------------------------------


def get_all_namespace_keys() -> dict[str, list[str]]:
    """Return namespace → list of identity key names for every relationship namespace.

    Used by tests to verify that every namespace classifies correctly.
    """
    result: dict[str, list[str]] = {}
    for ns, ref_keys in _get_entity_ref_targets().items():
        result[ns] = [rk.name for rk in ref_keys]
    for ns, lit in LITERAL_SCHEMAS.items():
        result[ns] = [lit.value_key]
    return result


def build_relationship_claim(
    field_name: str,
    identity: dict,
    exists: bool = True,
) -> tuple[str, dict]:
    """Return ``(claim_key, value)`` for a relationship claim.

    ``identity`` contains the identity fields for this relationship, e.g.,
    ``{"person": 42, "role": 5}``.

    The claim_key is derived from identity using the registry for *field_name*.
    The value dict includes identity fields plus ``exists``.
    """
    entity_refs = _get_entity_ref_targets()
    ref_keys = entity_refs.get(field_name)
    if ref_keys is not None:
        # Entity-reference namespace: key names are identity keys.
        expected = sorted(rk.name for rk in ref_keys)
        for key in expected:
            if key not in identity:
                raise ValueError(f"Missing required key {key!r} for {field_name!r}")
        identity_parts = {k: identity[k] for k in expected}
    else:
        literal = LITERAL_SCHEMAS.get(field_name)
        if literal is None:
            raise ValueError(f"Unknown relationship namespace: {field_name!r}")
        # Literal namespace: map value_key → identity_key.
        if literal.value_key not in identity:
            raise ValueError(
                f"Missing required key {literal.value_key!r} for {field_name!r}"
            )
        identity_parts = {literal.identity_key: identity[literal.value_key]}

    claim_key = make_claim_key(field_name, **identity_parts)
    value = {**identity, "exists": exists}
    return claim_key, value


def make_authoritative_scope(
    model_class: type[models.Model],
    object_ids,
) -> set[tuple[int, int]]:
    """Build an authoritative_scope set from a model class and object IDs.

    Convenience wrapper for the common single-content-type case used by
    ingest commands.
    """
    ct_id = ContentType.objects.get_for_model(model_class).pk
    return {(ct_id, obj_id) for obj_id in object_ids}
