"""Catalog activity rules."""

from __future__ import annotations

from apps.core.authz.predicates import email_verified, is_active, is_authenticated
from apps.core.authz.registry import register
from apps.core.authz.types import Activity

register(Activity.CATALOG_EDIT, is_authenticated, is_active, email_verified)
register(Activity.CATALOG_CREATE, is_authenticated, is_active, email_verified)
register(Activity.CATALOG_DELETE, is_authenticated, is_active, email_verified)
