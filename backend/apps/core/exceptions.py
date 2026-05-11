"""Shared base classes for structured API errors.

Subclasses declare ``kind`` and ``status`` as class-level constants and
implement ``to_body()`` to return the variant-specific body fields. The
single handler in ``config/api.py`` wraps the response uniformly:

    {"detail": {"kind": <kind>, "message": <message>, **to_body()}}

Use ``extra_headers()`` to attach response headers (e.g. ``Retry-After``).

Subclass dispatch is automatic: django-ninja's ``@api.exception_handler``
matches by ``isinstance`` (walks the MRO), so registering one handler
against ``StructuredApiError`` routes every subclass through it.
"""

from __future__ import annotations

from typing import Any, ClassVar


class StructuredApiError(Exception):
    """Base for exceptions that produce structured ``{detail: {kind, ...}}`` bodies."""

    kind: ClassVar[str]
    status: ClassVar[int]

    def __init_subclass__(cls, **kw: object) -> None:
        super().__init_subclass__(**kw)
        for attr in ("kind", "status"):
            if attr not in cls.__dict__:
                raise TypeError(f"{cls.__name__} must define class attribute {attr!r}")

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def to_body(self) -> dict[str, Any]:
        """Return variant-specific body fields. ``kind`` and ``message``
        are added by the handler; do not include them here."""
        return {}

    def extra_headers(self) -> dict[str, str]:
        """Optional response headers. Override for e.g. ``Retry-After``."""
        return {}
