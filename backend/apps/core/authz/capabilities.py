"""Build the target-less capability map for a given user.

Used by surfaces that answer "what may this user do?" without a
specific target in hand — today, the `/me/` endpoint. Target-aware
activities (e.g. `claim.revert`) are excluded; their verdicts come
from per-resource hints embedded in the resource's serializer.
"""

from __future__ import annotations

from collections.abc import Sequence

from .evaluator import check
from .registry import iter_rules
from .types import Activity, Allow, PolicyUser


def compute_capability_map(user: PolicyUser) -> dict[Activity, bool]:
    """Verdict for every target-less registered activity. Pure; no I/O.

    Anonymous callers go through the policy unchanged: every rule's
    first predicate is `is_authenticated`, so anonymous denies all.
    """
    return {
        rule.activity: isinstance(check(user, rule.activity), Allow)
        for rule in iter_rules()
        if not rule.target_aware
    }


def compute_row_capabilities(
    user: PolicyUser,
    target: object,
    activities: Sequence[Activity],
) -> dict[Activity, bool]:
    """Verdict for each target-aware ``activity`` against a single ``target``.

    Sibling to :func:`compute_capability_map` — that one builds the
    target-less map for ``/me/``; this one builds the per-row map a
    list endpoint embeds on each ChangeSet (or other resource) row.
    Pure; no I/O of its own — caller is responsible for any prefetch
    needed by the target Protocols.
    """
    return {
        activity: isinstance(check(user, activity, target=target), Allow)
        for activity in activities
    }
