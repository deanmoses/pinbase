"""Process-wide registry mapping each `Activity` to its predicate chain.

Per-app `authz.py` modules call `register(Activity.X, ...)` at startup
via each app's `apps.py: ready()`. Tests that mutate the registry use
the `isolated_registry` fixture so changes don't leak between tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from .predicates import Predicate
from .types import Activity


@dataclass(frozen=True)
class Rule:
    activity: Activity
    predicates: tuple[Predicate, ...]  # AND-conjunction; evaluated in order
    # True if the rule's verdict depends on a per-resource target. The
    # evaluator is unaffected (target is still passed through); the flag
    # exists so surfaces that answer "what may this user do?" target-less
    # — like `/me/capabilities` — can exclude these activities. A target-
    # aware rule's target-less verdict would be accurate-but-incomplete
    # (it's the floor across all targets), and consumers depending on
    # that floor would break the day per-row hints land.
    target_aware: bool = False
    # The narrow Protocol the rule's predicates read off the target. Set
    # only for target-aware rules whose predicates actually inspect the
    # target (not every target-aware rule does — `claim.revert` reserves
    # the wire slot for a future per-target predicate but its current
    # rule reads no target attributes). The system check in
    # `core/authz/checks.py` uses this to validate schema/activity
    # pairings declared via `policy_activities`.
    target: type | None = None


_REGISTRY: dict[Activity, Rule] = {}


def register(
    activity: Activity,
    *predicates: Predicate,
    target_aware: bool = False,
    target: type | None = None,
) -> None:
    """Register the rule for `activity`.

    Raises on duplicate registration. Raises on empty predicate list —
    a rule with no predicates would auto-allow every caller, which is
    almost certainly a misuse. A non-None ``target`` Protocol implies
    ``target_aware=True``; declaring ``target`` on a target-less rule
    is a programming error.
    """
    if not predicates:
        raise ValueError(
            f"Rule for {activity!r} requires at least one predicate; "
            f"an empty predicate list would auto-allow every caller."
        )
    if target is not None and not target_aware:
        raise ValueError(
            f"Rule for {activity!r} declares target={target.__name__} but "
            f"target_aware=False. A target Protocol only makes sense on a "
            f"target-aware rule."
        )
    if activity in _REGISTRY:
        raise RuntimeError(f"Rule for {activity!r} already registered")
    _REGISTRY[activity] = Rule(
        activity=activity,
        predicates=predicates,
        target_aware=target_aware,
        target=target,
    )


def get_rule(activity: Activity) -> Rule | None:
    return _REGISTRY.get(activity)


def iter_rules() -> tuple[Rule, ...]:
    return tuple(_REGISTRY.values())


def _snapshot() -> dict[Activity, Rule]:
    """Internal — used only by the `isolated_registry` test fixture."""
    return dict(_REGISTRY)


def _restore(snapshot: dict[Activity, Rule]) -> None:
    """Internal — used only by the `isolated_registry` test fixture."""
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)
