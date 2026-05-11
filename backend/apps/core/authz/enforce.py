"""Enforcement entry point: run ``check()``, log, raise on Deny.

Kept separate from ``markers.py`` (whose job is metadata stamping) and
from ``evaluator.py`` (which is bound by "no I/O in policy" — this
module logs and raises, both of which are I/O-shaped).

Both ``@requires`` and future inline target-aware call sites funnel
through ``enforce()`` so audit logging and the structured 403 happen in
exactly one place.
"""

from __future__ import annotations

import logging

from .evaluator import check
from .exceptions import PolicyDeniedError
from .types import Activity, Deny, PolicyContext, PolicyUser

log = logging.getLogger("authz")


def enforce(
    user: PolicyUser,
    activity: Activity,
    target: object | None = None,
    context: PolicyContext | None = None,
) -> None:
    """Evaluate ``activity`` and raise :class:`PolicyDeniedError` on deny.

    Allows are logged at DEBUG (mostly off in prod); denials at INFO
    with ``(user_id, activity, code, target_id)`` so audit search can
    tie a denial back to the affected row. ``target_id`` is ``None``
    for target-less activities.
    ``LookupError`` from an unregistered activity propagates as a 500 —
    the registry-completeness test keeps that branch dead.
    """
    decision = check(user, activity, target=target, context=context)
    # `target` is typed `object | None` at the engine layer (the engine
    # never reads attributes off it; predicates do, via their narrow
    # Protocols). The audit log is an I/O boundary that wants the row
    # id when the target is a Django model — `getattr` is the
    # documented escape for boundary reads of optional attributes.
    target_id = getattr(target, "id", None) if target is not None else None
    if isinstance(decision, Deny):
        log.info(
            "authz.deny",
            extra={
                "user_id": user.id,
                "activity": activity.value,
                "code": decision.code.value,
                "target_id": target_id,
            },
        )
        raise PolicyDeniedError(decision)
    log.debug(
        "authz.allow",
        extra={
            "user_id": user.id,
            "activity": activity.value,
            "target_id": target_id,
        },
    )
