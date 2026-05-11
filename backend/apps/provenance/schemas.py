"""API schemas for the provenance app.

Used by api.py and the page-oriented changes endpoints (page_endpoints.py).

Claim payloads are stored as JSON (``Claim.value`` is a ``JSONField``), so
``old_value`` / ``new_value`` / ``value`` fields are typed as ``object`` —
they carry scalars, dicts, lists, or null depending on the claim kind, and
the catalog-level schema is what actually constrains each field's shape.
"""

from __future__ import annotations

from typing import ClassVar

from django.db.models import Model
from ninja import Field, Schema

from apps.core.authz import Activity

from .models.changeset import ChangeSet


class FieldChangeSchema(Schema):
    """A single field change within a ChangeSet (old -> new)."""

    field_name: str
    claim_key: str
    old_value: object | None = None
    new_value: object
    claim_id: int | None = None
    claim_user_id: int | None = None
    is_active: bool | None = None
    is_winning: bool | None = None
    is_retracted: bool | None = None


class RetractionSchema(Schema):
    claim_id: int
    field_name: str
    claim_key: str
    old_value: object


class ChangeSetBaseSchema(Schema):
    """Common fields for any read-side ChangeSet representation."""

    id: int
    user_display: str | None = None
    note: str
    created_at: str


class ChangeSetSchema(ChangeSetBaseSchema):
    """A grouped edit session with per-field diffs.

    ``capabilities`` is the wire contract for every ChangeSet row variant
    in the codebase — see also ``ChangeSetSummarySchema``,
    ``ChangeSetDetailSchema``, ``CitedChangeSetSchema``, and
    ``UserChangeSetSchema``. The contract:

    Each entry answers "is the caller authorized to *attempt* this
    activity on this row" — it is **not** a guarantee the action will
    succeed. ``capabilities['changeset.undo'] is True`` only means the
    policy lets this caller call the undo endpoint with this changeset;
    the endpoint additionally enforces operational invariants
    (``action == DELETE``, claims not superseded) that aren't expressible
    as pure-attribute policy predicates and so don't reflect on the wire.

    A future per-row Undo UI MUST AND the embedded verdict with operational
    eligibility before rendering an affordance, or design a separate
    operational-eligibility wire field at that time.
    """

    changes: list[FieldChangeSchema]
    retractions: list[RetractionSchema] = []
    capabilities: dict[Activity, bool] = Field(default_factory=dict)

    # Declared on each concrete row variant (not on the base) — the
    # ``authz.E101–E106`` system check reads these from ``__dict__``,
    # so inherited declarations don't trigger the structural check.
    policy_activities: ClassVar[tuple[Activity, ...]] = (Activity.CHANGESET_UNDO,)
    policy_target_model: ClassVar[type[Model]] = ChangeSet


class ClaimSchema(Schema):
    """A single per-field claim as surfaced to the Sources UI."""

    source_name: str | None = None
    source_slug: str | None = None
    user_display: str | None = None  # username for user-attributed claims
    field_name: str
    value: object
    citation: str
    created_at: str
    is_winner: bool
    changeset_note: str | None = None


class CitationReferenceInputSchema(Schema):
    """Reference an existing CitationInstance to clone onto a user edit."""

    citation_instance_id: int


class ChangeSetInputSchema(Schema):
    """Base shape for any user-attributed mutation that produces a ChangeSet."""

    note: str = ""
    citation: CitationReferenceInputSchema | None = None


class AttributionSchema(Schema):
    """License and source attribution for rendered content."""

    license_slug: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    permissiveness_rank: int | None = None
    requires_attribution: bool = False
    source_name: str | None = None
    source_url: str | None = None
    attribution_text: str | None = None


class ReviewLinkSchema(Schema):
    """A link out to an external page relevant to a needs-review item."""

    label: str
    url: str


class CitationLinkSchema(Schema):
    """A link attached to a citation source."""

    url: str
    label: str


class InlineCitationSchema(Schema):
    """Metadata for an inline citation in rendered markdown."""

    id: int
    index: int
    source_name: str
    source_type: str
    author: str
    year: int | None = None
    locator: str
    links: list[CitationLinkSchema] = []


class RichTextSchema(Schema):
    """A text field bundled with rendered HTML plus provenance metadata."""

    text: str = ""
    html: str = ""
    citations: list[InlineCitationSchema] = []
    attribution: AttributionSchema | None = None


class CitationSourceSchema(Schema):
    name: str
    slug: str
    source_type: str
    priority: int
    url: str
    description: str


class ReviewClaimSchema(Schema):
    id: int
    source_name: str
    field_name: str
    # ``value`` is the raw JSONField payload of a claim — scalar, dict, list,
    # or null depending on the field — and stays ``object`` for the same
    # reason the shared schemas above do.
    value: object
    needs_review_notes: str
    created_at: str
    # Context about the subject (the entity this claim targets).
    # Canonical hyphenated CatalogModel.entity_type, e.g. "manufacturer".
    subject_type: str
    subject_name: str
    subject_slug: str | None = None
    # Title that this claim created (for group claims).
    title_slug: str | None = None
    review_links: list[ReviewLinkSchema] = []


class RevertNoteSchema(Schema):
    note: str


class UndoChangeSetSchema(Schema):
    note: str = ""


class UndoResultSchema(Schema):
    changeset_id: int


class CitationInstanceSchema(Schema):
    id: int
    citation_source_id: int
    citation_source_name: str
    claim_id: int | None = None
    locator: str
    created_at: str


class CitationInstanceBatchSchema(Schema):
    id: int
    source_name: str
    source_type: str
    author: str
    year: int | None = None
    locator: str
    links: list[CitationLinkSchema] = []


class CitationInstanceCreateSchema(Schema):
    citation_source_id: int
    locator: str = ""
