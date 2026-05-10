"""Route-inventory test: every mutating route is gated or explicitly public.

Walks every Ninja router in the project and asserts every mutating
operation carries exactly one of:

    @requires(Activity.X)        — the canonical gate; enforced at request time.
    @gated_inline(Activity.X)    — view body calls policy.check() itself.
    @public_mutation(reason)     — deliberately ungated; reason captured.

A mutating route with no marker (or with two) fails the test. There is
no allowlist file — every exception is the @public_mutation decorator
at the view, where the reason lives next to the route.
"""

from __future__ import annotations

from apps.core.authz.markers import (
    ACTIVITY_ATTR,
    GATED_INLINE_ATTR,
    PUBLIC_ATTR,
)
from apps.core.authz.route_walker import iter_operations
from apps.core.authz.types import Activity
from config.api import api

# `op.methods` from Ninja is uppercase. Do NOT reuse the lowercase
# MUTATING_METHODS constant in `test_openapi_boundaries.py:34` — that
# one reads from OpenAPI introspection (which lowercases methods).
# Wrong casing here would silently classify every mutating route as
# non-mutating and the test would pass vacuously.
MUTATING_METHODS = frozenset({"POST", "PATCH", "DELETE"})

MARKER_ATTRS = (ACTIVITY_ATTR, GATED_INLINE_ATTR, PUBLIC_ATTR)


def test_every_mutating_route_is_classified() -> None:
    # Canary: route_walker reaches into django-ninja internals
    # (api._routers, path_view.operations, op.view_func). If a future
    # ninja release renames any of those, the walker silently yields
    # zero and every assertion below passes vacuously. The pin in
    # backend/pyproject.toml (`django-ninja>=1.3,<2`) makes a major
    # bump deliberate; this floor catches a structural change within
    # the pinned range. Project had 97 mutating routes when this floor
    # was set — bump if that drops legitimately.
    mutating = [(m, p, v) for m, p, v in iter_operations(api) if m in MUTATING_METHODS]
    assert len(mutating) >= 50, (
        f"route_walker yielded only {len(mutating)} mutating routes — "
        "django-ninja internals may have shifted. See route_walker.py."
    )

    unclassified: list[str] = []
    for method, path, view in mutating:
        present = [name for name in MARKER_ATTRS if hasattr(view, name)]
        route_id = f"{method} {path} → {view.__module__}.{view.__qualname__}"

        # Belt-and-braces: a view double-stamped (e.g. both @requires
        # and @gated_inline by accident, or a copy-paste during the
        # migration) would silently pass a first-wins check. Make it
        # loud instead.
        assert len(present) <= 1, f"{route_id}: multiple markers {present}"

        if not present:
            unclassified.append(route_id)
            continue

        [marker] = present
        value = getattr(view, marker)
        if marker == PUBLIC_ATTR:
            assert isinstance(value, str), (
                f"{route_id}: @public_mutation reason must be a string"
            )
            assert value.strip(), f"{route_id}: empty @public_mutation reason"
        else:
            # isinstance, not `value in Activity` — StrEnum's `in`
            # accepts bare strings by value (3.12+), so the looser
            # check would let a hand-stamped
            # `_authz_activity = "catalog.edit"` pass.
            assert isinstance(value, Activity), (
                f"{route_id}: non-Activity marker value {value!r}"
            )

    assert not unclassified, (
        "Unclassified mutating routes (each needs @requires, "
        "@gated_inline, or @public_mutation):\n  " + "\n  ".join(unclassified)
    )
