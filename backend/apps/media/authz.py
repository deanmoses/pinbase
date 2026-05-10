"""Media activity rules."""

from __future__ import annotations

from apps.core.authz.predicates import email_verified, is_active, is_authenticated
from apps.core.authz.registry import register
from apps.core.authz.types import Activity

register(Activity.MEDIA_EDIT, is_authenticated, is_active, email_verified)
