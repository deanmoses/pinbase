"""Cross-app shared types."""

from __future__ import annotations

from typing import NamedTuple


class EntityKey(NamedTuple):
    """Hashable reference to a catalog entity via content-type + object id.

    Used both as a dict key and as the input shape for helpers that fan out
    across content types (e.g. ``batch_resolve_entities``).
    """

    content_type_id: int
    object_id: int


class ClaimIdentity(NamedTuple):
    """Hashable identity of a claim on an entity.

    Matches the ``(content_type, object_id, claim_key)`` uniqueness scope
    used by provenance writes and catalog ingest when deduplicating
    pending claims or joining against existing active rows.
    """

    content_type_id: int
    object_id: int
    claim_key: str
