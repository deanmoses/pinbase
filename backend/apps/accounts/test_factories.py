"""Test-only factories for accounts models.

Kept outside ``tests/`` so test helpers can be imported across apps
without circular dependencies or duplicated conftest fixtures.

Reach for ``make_user`` when a test needs defaults, multiple distinct
users in one test, or to opt into a future ``User`` field default
(e.g. ``email_verified``). Tests that want a specific email value can
keep calling ``User.objects.create_user`` directly.
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
    return User.objects.create_user(email=email, **overrides)
