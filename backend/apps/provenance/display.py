"""Build structured display values for relationship-claim values in edit history.

A relationship claim's stored value is a dict like
``{"person": 13, "role": 9, "exists": true}`` — fine for the data model,
unfriendly for users. This module turns those into a
:class:`~apps.provenance.schemas.ClaimDisplayValueSchema` — an ordered list of
identity parts (each resolved to a user-facing label) and qualifier parts
(scalars left as-is for the frontend to render). Layout decisions
(separators, ``×N`` count suffixes, parentheses around categories) live on
the frontend; the backend's job is FK-pk-to-label resolution.

Usage::

    labels = resolve_labels([FieldValue(field_name, value), ...])
    bundled = claim_value(field_name, value, labels)  # {raw, display}

``resolve_labels`` queries one row per FK target model (no per-row N+1).
Bare scalars (direct-field claims like ``technology_generation``) and
unregistered namespaces return ``None`` — clients fall back to the raw
value in that case.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import NamedTuple

from django.db.models import Model

from .schemas import (
    ClaimDisplayIdentityPartSchema,
    ClaimDisplayIdentityState,
    ClaimDisplayQualifierPartSchema,
    ClaimDisplayValueSchema,
    ClaimValueSchema,
)
from .validation import (
    RelationshipSchema,
    ValueKeySpec,
    get_display_override,
    get_relationship_schema,
)

logger = logging.getLogger(__name__)


class _LabelResult(NamedTuple):
    """A resolved identity label plus its state discriminant.

    Two-return-value plumbing for the engine: ``state`` says which case
    we're in, ``label`` carries the resolved string when ``state ==
    "resolved"`` and is None otherwise. The Schema mirrors this shape;
    rendering decisions for the non-resolved states are the frontend's.
    """

    label: str | None
    state: ClaimDisplayIdentityState


# A relationship claim's value payload: a dict with ``exists: bool`` plus
# the namespace-specific keys declared in :class:`ValueKeySpec`. Per-key
# types vary by namespace (int pks, optional counts, str literals); schema
# validation enforces shape at the data-layer boundary.
RelationshipClaimValue = Mapping[str, object]


class FieldValue(NamedTuple):
    """A claim value paired with the field name that interprets it.

    The field name picks which relationship schema applies; the value is the
    raw payload. Callers feed :func:`resolve_labels` with these so FK pks
    can be collected for batched resolution.
    """

    field_name: str
    value: object


class FkRef(NamedTuple):
    """A reference to a specific row in an FK target model."""

    model: type[Model]
    pk: int


class LabelLookup:
    """Display labels resolved from :class:`FkRef`\\ s.

    Built once per response by :func:`resolve_labels`; consulted by the
    display engine when it needs to turn a pk into a name.
    """

    __slots__ = ("_labels",)

    def __init__(self) -> None:
        self._labels: dict[FkRef, str] = {}

    def add(self, ref: FkRef, label: str) -> None:
        self._labels[ref] = label

    def get(self, ref: FkRef) -> str | None:
        return self._labels.get(ref)


def _fk_label(
    value: RelationshipClaimValue,
    schema: RelationshipSchema,
    spec: ValueKeySpec,
    labels: LabelLookup,
) -> _LabelResult:
    """Resolve a spec's FK value into a ``_LabelResult``.

    Returns ``(None, "missing")`` when the claim dict carries no value
    for the key — an invariant violation that validation rule 4 should
    prevent (logged loudly so it's observable). Returns ``(None,
    "deleted")`` when the pk is present but the target row no longer
    exists — a legitimate runtime condition. Otherwise returns the
    resolved label with ``state="resolved"``.
    """
    assert spec.fk_target is not None, (
        f"{schema.namespace!r}.{spec.name!r} is not declared as an FK"
    )
    # Display assumes pk lookups. Validation honours ``lookup_field``, so a
    # future ``FkTarget(Model, "slug")`` registration would silently miss
    # labels here. Fail loud until that case is actually needed.
    assert spec.fk_target.lookup_field == "pk", (
        f"{schema.namespace!r}.{spec.name!r} uses non-pk lookup "
        f"{spec.fk_target.lookup_field!r}; display only supports pk"
    )
    pk = value.get(spec.name)
    if pk is None:
        # Invariant violation: validation rule 4 (required identity keys)
        # should prevent this. If we got here, something bypassed the
        # write-time validator — pre-validation data, an ingest source
        # that skipped validation, or a future bug. Log loudly so it's
        # observable in monitoring; emit state="missing" so the frontend
        # can render a placeholder without crashing the page.
        logger.error(
            "display: missing identity key %r in namespace %r — validation "
            "rule 4 should prevent this; value=%r",
            spec.name,
            schema.namespace,
            dict(value),
        )
        return _LabelResult(label=None, state="missing")
    # ``type(pk) is int`` (not ``isinstance``): ``isinstance(True, int)`` is
    # ``True`` and would let a stray bool slip through as a pk. Schema
    # validation rule 5 rejects wrong-type values at write time, so reaching
    # here means the same kind of integrity breach as ``pk is None``: log
    # and degrade, don't 500 the whole edit-history page.
    if type(pk) is not int:
        logger.error(
            "display: non-int pk %r (%s) for identity key %r in namespace %r — "
            "validation rule 5 should prevent this; value=%r",
            pk,
            type(pk).__name__,
            spec.name,
            schema.namespace,
            dict(value),
        )
        return _LabelResult(label=None, state="missing")
    label = labels.get(FkRef(spec.fk_target.model, pk))
    if label is None:
        return _LabelResult(label=None, state="deleted")
    return _LabelResult(label=label, state="resolved")


def resolve_identity_label(
    value: RelationshipClaimValue,
    schema: RelationshipSchema,
    spec: ValueKeySpec,
    labels: LabelLookup,
) -> _LabelResult:
    """Resolve one identity slot into a ``_LabelResult``.

    Composes :func:`get_display_override` (declarative display_key
    substitution) with :func:`_fk_label` (FK pk → label) and the canonical
    scalar fallback. The override and resolved-scalar paths always return
    ``state="resolved"``; missing-key paths log and return
    ``state="missing"``.
    """
    assert spec.identity is not None, (
        f"resolve_identity_label called on non-identity spec {spec.name!r}"
    )
    override = get_display_override(value, schema, spec.name)
    if override is not None:
        return _LabelResult(label=str(override), state="resolved")
    if spec.fk_target is not None:
        return _fk_label(value, schema, spec, labels)
    # Canonical scalar fallback. ``is not None`` (not truthy) so a
    # deliberately empty identity renders as the empty string rather than
    # state="missing" — matches the prior abbreviation behavior.
    # Absent key (invariant violation) → state="missing" + loud log.
    raw = value.get(spec.name)
    if raw is None:
        logger.error(
            "display: missing scalar identity key %r in namespace %r — "
            "validation rule 4 should prevent this; value=%r",
            spec.name,
            schema.namespace,
            dict(value),
        )
        return _LabelResult(label=None, state="missing")
    return _LabelResult(label=str(raw), state="resolved")


def _collect_refs(items: Iterable[FieldValue]) -> set[FkRef]:
    """Walk :class:`FieldValue`\\ s and gather every FK reference.

    Non-dict values and direct-field claims (unregistered namespaces) are
    skipped — they have no FKs to resolve. Corrupt pk values (None, wrong
    type) are also skipped silently here; ``_fk_label`` is the canonical
    log site for those violations so we don't double-log when the same
    claim flows through both functions during a single response.
    """
    refs: set[FkRef] = set()
    for field_name, value in items:
        if not isinstance(value, dict):
            continue
        schema = get_relationship_schema(field_name)
        if schema is None:
            continue
        for spec in schema.value_keys:
            if spec.fk_target is None:
                continue
            # Display-engine limitation. Same check fires in ``_fk_label``;
            # consider hoisting to ``register_relationship_schema`` if a
            # second site ever needs it.
            assert spec.fk_target.lookup_field == "pk", (
                f"{field_name!r}.{spec.name!r} uses non-pk lookup "
                f"{spec.fk_target.lookup_field!r}; display only supports pk"
            )
            pk = value.get(spec.name)
            # Don't crash on data-integrity violations — ``_fk_label`` logs
            # and degrades to ``state="missing"`` for the same row when it
            # processes the value later in the request.
            if type(pk) is not int:
                continue
            refs.add(FkRef(spec.fk_target.model, pk))
    return refs


def resolve_labels(items: Iterable[FieldValue]) -> LabelLookup:
    """Build a :class:`LabelLookup` for all relationship claims in ``items``.

    One query per FK target model. Resolved labels are ``str(instance)``,
    so each FK target model is expected to define a meaningful ``__str__``.
    Missing rows (referent deleted) simply don't appear in the result;
    callers (``_fk_label``) emit ``state="deleted"`` for those refs.
    """
    pks_by_model: dict[type[Model], set[int]] = defaultdict(set)
    for ref in _collect_refs(items):
        pks_by_model[ref.model].add(ref.pk)

    lookup = LabelLookup()
    for model, pks in pks_by_model.items():
        for inst in model._default_manager.filter(pk__in=pks):
            lookup.add(FkRef(model, inst.pk), str(inst))
    return lookup


def build_display_value(
    field_name: str, value: object, labels: LabelLookup
) -> ClaimDisplayValueSchema | None:
    """Return a structured display rendering for a relationship-claim value.

    Returns ``None`` when ``value`` isn't a relationship-claim dict —
    direct-field scalars and unknown namespaces fall through, and the
    frontend renders the raw value.

    Generic engine: identity slots are emitted in declaration order via
    :func:`resolve_identity_label`; non-identity, non-display-override
    specs are emitted as ``ClaimDisplayQualifierPartSchema`` entries in
    declaration order. Absent qualifier keys are skipped; present-but-
    falsy qualifiers (``None``, ``False``, ``0``, ``""``) are emitted —
    "should this be visible to the user" is the frontend's job.
    """
    if not isinstance(value, dict):
        return None
    schema = get_relationship_schema(field_name)
    if schema is None:
        return None

    # display_key targets are consumed by their identity spec's rendering;
    # they must not also surface as qualifiers.
    consumed_by_display: set[str] = {
        s.display_key for s in schema.value_keys if s.display_key is not None
    }

    identity_parts: list[ClaimDisplayIdentityPartSchema] = []
    qualifier_parts: list[ClaimDisplayQualifierPartSchema] = []

    for spec in schema.value_keys:
        if spec.identity is not None:
            result = resolve_identity_label(value, schema, spec, labels)
            identity_parts.append(
                ClaimDisplayIdentityPartSchema(
                    key=spec.name,
                    label=result.label,
                    state=result.state,
                )
            )
            continue

        if spec.name in consumed_by_display:
            continue

        if spec.name not in value:
            continue

        raw = value[spec.name]
        if spec.fk_target is not None:
            # TODO(qualifier-fk): no schema has non-identity FKs today; this
            # branch exists for symmetry with the identity FK path. The
            # state discriminant has nowhere to surface on
            # ``ClaimDisplayQualifierPartSchema``, so ``deleted`` and
            # ``missing`` both silently collapse to ``value=None`` here.
            # When the first qualifier-FK schema is registered, widen
            # ``ClaimDisplayQualifierPartSchema`` with a ``state`` field
            # rather than shipping with the silent collapse.
            qualifier_parts.append(
                ClaimDisplayQualifierPartSchema(
                    key=spec.name,
                    value=_fk_label(value, schema, spec, labels).label,
                )
            )
            continue

        # Pass the typed value through. ``bool`` stays bool through this
        # Python-side path because ``raw`` keeps its runtime type — the
        # Pydantic-side coercion risk (True → 1) is handled at the Schema
        # by ordering ``bool`` before ``int`` in the union. Unexpected
        # types get stringified (schema validation should have caught any).
        scalar: bool | int | str | None = (
            raw if raw is None or isinstance(raw, bool | int | str) else str(raw)
        )
        qualifier_parts.append(
            ClaimDisplayQualifierPartSchema(key=spec.name, value=scalar)
        )

    return ClaimDisplayValueSchema(identity=identity_parts, qualifiers=qualifier_parts)


def claim_value(
    field_name: str, value: object, labels: LabelLookup
) -> ClaimValueSchema:
    """Bundle a raw claim value with its structured display rendering."""
    return ClaimValueSchema(
        raw=value, display=build_display_value(field_name, value, labels)
    )
