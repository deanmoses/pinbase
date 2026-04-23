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
