"""Utilities for bulk ingest operations."""

from __future__ import annotations

from django.utils.text import slugify

MAX_NAMES_SHOWN = 10


def format_names(names: list[str]) -> str:
    """Format a list of names for summary output, truncating if long."""
    if len(names) <= MAX_NAMES_SHOWN:
        return ", ".join(names)
    return ", ".join(names[:MAX_NAMES_SHOWN]) + f", ... ({len(names)} total)"


def generate_unique_slug(base_name: str, existing_slugs: set[str]) -> str:
    """Generate a unique slug, tracking used slugs in the provided set.

    Mimics the slug generation in model save() methods but works with
    bulk_create() which skips save(). Mutates ``existing_slugs`` by adding
    the generated slug so subsequent calls won't collide.
    """
    base = slugify(base_name) or "item"
    slug = base
    counter = 2
    while slug in existing_slugs:
        slug = f"{base}-{counter}"
        counter += 1
    existing_slugs.add(slug)
    return slug
