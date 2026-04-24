"""Cross-app shared types."""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple

# JSON-shaped dict — object keys, arbitrary JSON values. ``object`` (not
# ``Any``) forces callers to isinstance-narrow before use, which matches
# the free-form-but-typed nature of JSON.
#
# ``JsonBody`` (invariant dict): test-client request/response bodies.
# ``JsonData`` (covariant Mapping): read-only views of JSON — function
# params that only read, e.g. ``extra_data`` JSONField contents. A
# covariant alias is needed because dict literals like
# ``{"k": [1, 2]}`` have inferred type ``dict[str, list[int]]``, which
# is not a subtype of ``dict[str, object]`` but is a subtype of
# ``Mapping[str, object]``.
type JsonBody = dict[str, object]
type JsonData = Mapping[str, object]


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
