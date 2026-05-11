"""Helper for asserting a target-aware predicate runs zero queries.

Every target-aware predicate must have at least one test that wraps the
call in ``CaptureQueriesContext`` and asserts a zero-query budget.
Static type checking covers the typical mistake (reading an attribute
outside the Protocol) but not dynamic access or a Protocol that
declares an FK relation the caller forgot to prefetch.

This helper exists so each call site reads as "this predicate must be
pure" rather than rebuilding the assertion inline.
"""

from __future__ import annotations

from typing import Any

from django.db import connection
from django.test.utils import CaptureQueriesContext

from .predicates import Predicate
from .types import Decision, PolicyContext, PolicyUser


def assert_predicate_is_pure(
    predicate: Predicate,
    user: PolicyUser,
    target: Any = None,  # noqa: ANN401 — see docstring
    context: PolicyContext | None = None,
) -> Decision:
    """Run ``predicate`` and assert it issued zero database queries.

    Returns the predicate's decision so the caller can additionally
    assert on the verdict shape. Raises ``AssertionError`` with the
    captured query log if any query ran.

    ``target`` is typed ``Any`` to match the registry-facing
    :data:`Predicate` alias — per-rule predicates declare their own
    narrow Protocol on the parameter; the helper stays generic.
    """
    with CaptureQueriesContext(connection) as ctx:
        decision = predicate(user, target, context)
    if len(ctx) != 0:
        queries = "\n".join(q["sql"] for q in ctx.captured_queries)
        raise AssertionError(
            f"predicate {getattr(predicate, '__name__', predicate)!r} "
            f"ran {len(ctx)} quer{'y' if len(ctx) == 1 else 'ies'} but "
            f"must be pure:\n{queries}"
        )
    return decision
