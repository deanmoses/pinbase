"""Marker decorators that classify mutating routes and gate enforcement.

`@requires` is the canonical gate: it wraps the view to call
``enforce(request.user, activity)``, raising :class:`PolicyDeniedError`
on deny, and stamps an ``Activity`` marker the inventory walker reads
off the wrapped callable.

`@gated_inline` is for routes that can't fit the single-decorator form
(multiple activities, branch on decision, etc.) and call ``enforce()``
or ``check()`` inline. The decorator stays stamp-only — it exists so
the inventory test still recognizes the route as gated; the inline
call is what enforces.

`@public_mutation` declares a route as deliberately ungated, with the
reason captured in the inventory output for later audit.

Marker reads go through the typed accessors at the bottom of this
module (``get_required_activity`` / ``get_gated_inline_activity`` /
``get_public_reason``) — never via ``getattr(view, "_authz_…")``,
which is string-keyed and erases the type.
"""

from __future__ import annotations

import functools
import types
from collections.abc import Callable
from typing import TypeVar, cast

from .enforce import enforce
from .types import Activity

F = TypeVar("F", bound=Callable[..., object])

# Attribute names the inventory walker reads. Centralized so the walker,
# the markers, and any forward-compat wrapper agree on the wire format.
ACTIVITY_ATTR = "_authz_activity"
GATED_INLINE_ATTR = "_authz_gated_inline"
PUBLIC_ATTR = "_authz_public"


def requires(activity: Activity) -> Callable[[F], F]:
    """Wrap the view to enforce `activity` and stamp the inventory marker.

    The wrapper calls ``enforce(request.user, activity)``, which raises
    :class:`PolicyDeniedError` on a ``Deny`` decision. The marker is
    set on the wrapped callable (the object Ninja resolves
    ``op.view_func`` to), so the inventory walker sees it on the right
    object.

    Decorator order matters: ``@requires`` must be *inside*
    ``@router.<verb>`` so Ninja registers the wrapped callable.
    Reversing the stack puts the marker on the Ninja-wrapped operation
    and the walker misses it.
    """

    def decorator(func: F) -> F:
        # Bind `enforce` as a closure cell rather than a module global
        # so the wrapper's body resolves correctly after we swap
        # ``__globals__`` (see ``types.FunctionType`` call below).
        _enforce = enforce

        def template(request, *args, **kwargs):  # type: ignore[no-untyped-def]
            _enforce(request.user, activity)
            return func(request, *args, **kwargs)

        # Ninja resolves forward-ref annotations via
        # `getattr(view, "__globals__", {})` (see
        # ``ninja.signature.utils.get_typed_signature``). A plain wrapper
        # defined here would carry *this* module's globals, so Ninja
        # would fail to resolve any annotation that lives in the wrapped
        # function's module (e.g. closure-scoped types in factory-built
        # CRUD views). Rebuild the wrapper as a ``FunctionType`` carrying
        # the wrapped function's globals while keeping the closure cells
        # (``enforce``, ``activity``, ``func``) the body references.
        # ``update_wrapper`` then copies ``__name__`` / ``__qualname__`` /
        # ``__doc__`` / ``__annotations__`` / ``__wrapped__`` from ``func``,
        # which is what makes the equivalent of ``@functools.wraps`` —
        # we just can't apply ``@wraps`` directly because we need to
        # control ``__globals__``.
        wrapper = types.FunctionType(
            template.__code__,
            func.__globals__,
            name=template.__name__,
            argdefs=template.__defaults__,
            closure=template.__closure__,
        )
        functools.update_wrapper(wrapper, func)
        setattr(wrapper, ACTIVITY_ATTR, activity)
        # ``types.FunctionType`` returns a ``FunctionType`` instance,
        # which mypy treats as ``Callable[..., Any]`` — it can't verify
        # that a reflectively-constructed function has signature ``F``.
        # At runtime the signature *is* preserved (``update_wrapper``
        # copied ``__signature__`` / ``__annotations__`` / ``__wrapped__``
        # from ``func``), but that's runtime knowledge static analysis
        # can't see through. The cast is the irreducible gap between
        # reflective function construction and the type system, not a
        # papered-over mistake.
        return cast(F, wrapper)

    return decorator


def gated_inline(activity: Activity) -> Callable[[F], F]:
    """Mark a view whose enforcement is inline in the body.

    Always stamp-only. The marker itself does not call ``enforce()``;
    the route body must call ``enforce()`` (or ``check()``) once a
    target-aware predicate exists. Until then, the route is gated only
    by Django auth + ``WorkOSBackend.get_user``'s ``is_active=True``
    filter — which already enforces the launch rules for these routes.

    The decorator's only job is to declare the activity to the
    inventory test; flipping it to call ``enforce()`` here would
    double-evaluate once the inline call lands.
    """

    def decorator(func: F) -> F:
        setattr(func, GATED_INLINE_ATTR, activity)
        return func

    return decorator


def public_mutation(reason: str) -> Callable[[F], F]:
    """Declare a mutating route as deliberately ungated.

    `reason` is required and must be non-empty after `.strip()` — an
    empty or whitespace-only rationale fails at decoration time so a
    missing reason can't slip into the inventory output.
    """
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError(
            "@public_mutation requires a non-empty reason string. "
            "The reason is captured in the inventory output so a future "
            "reviewer can audit 'do we still want this public?'."
        )

    def decorator(func: F) -> F:
        setattr(func, PUBLIC_ATTR, reason)
        return func

    return decorator


# ── Typed marker read accessors ──────────────────────────────────────
#
# The marker attributes are string-keyed (`setattr`/`getattr`), which
# means consumers can't read them in a typed way without each call site
# repeating an `isinstance` narrowing dance. These accessors centralize
# the read protocol: every consumer (route walker, inventory test,
# enforcement tests) goes through them and gets a properly typed value
# back.


def get_required_activity(view: object) -> Activity | None:
    """Return the ``Activity`` stamped by ``@requires``, or ``None``."""
    value = getattr(view, ACTIVITY_ATTR, None)
    return value if isinstance(value, Activity) else None


def get_gated_inline_activity(view: object) -> Activity | None:
    """Return the ``Activity`` stamped by ``@gated_inline``, or ``None``."""
    value = getattr(view, GATED_INLINE_ATTR, None)
    return value if isinstance(value, Activity) else None


def get_public_reason(view: object) -> str | None:
    """Return the rationale stamped by ``@public_mutation``, or ``None``."""
    value = getattr(view, PUBLIC_ATTR, None)
    return value if isinstance(value, str) else None
