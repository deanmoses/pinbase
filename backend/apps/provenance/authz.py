"""Provenance activity rules."""

from __future__ import annotations

from apps.core.authz.predicates import email_verified, is_active, is_authenticated
from apps.core.authz.registry import register
from apps.core.authz.types import Activity

register(Activity.CLAIM_REVERT, is_authenticated, is_active, email_verified)
register(Activity.CHANGESET_UNDO, is_authenticated, is_active, email_verified)
