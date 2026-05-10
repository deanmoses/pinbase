"""Test-only factories for accounts models.

Kept outside ``tests/`` so test helpers can be imported across apps
without circular dependencies or duplicated conftest fixtures.

Always prefer ``make_user`` over ``User.objects.create_user`` in tests
so every site picks up future ``User`` field defaults (e.g.
``email_verified``) without per-call overrides. Pass ``email=...`` when
the literal value is what the test asserts on.
"""

from __future__ import annotations

import uuid
from typing import Any

from .models import User


def make_user(
    *,
    email: str | None = None,
    **overrides: Any,  # noqa: ANN401 - matches UserManager.create_user signature.
) -> User:
    """Create a ``User`` for tests with sensible defaults.

    The default email is unique per call (UUID suffix) so a test that
    needs two distinct users can call ``make_user()`` twice without
    collision. Tests that care about the exact email pass it explicitly.
    """
    if email is None:
        email = f"editor-{uuid.uuid4().hex[:8]}@example.com"
    overrides.setdefault("email_verified", True)
    return User.objects.create_user(email=email, **overrides)
