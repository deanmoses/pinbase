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


class ManufacturerResolver:
    """Resolve manufacturer names to slugs, auto-creating on miss.

    Caches name→slug and trade_name→slug lookups from the database at
    construction time.  Also loads CorporateEntity name→manufacturer slug
    for IPDB's 3-priority resolution cascade.

    All lookups are case-insensitive.
    """

    def __init__(self) -> None:
        from apps.catalog.models import CorporateEntity, Manufacturer

        self._name_to_slug: dict[str, str] = {}
        self._slugs: set[str] = set()
        for m in Manufacturer.objects.all():
            self._name_to_slug[m.name.lower()] = m.slug
            if m.trade_name:
                self._name_to_slug[m.trade_name.lower()] = m.slug
            self._slugs.add(m.slug)

        self._entity_to_slug: dict[str, str] = {
            ce.name.lower(): ce.manufacturer.slug
            for ce in CorporateEntity.objects.select_related("manufacturer").all()
        }

    def resolve(self, name: str) -> str | None:
        """Look up a manufacturer by name or trade name. Returns slug or None."""
        return self._name_to_slug.get(name.lower())

    def resolve_entity(self, name: str) -> str | None:
        """Look up a manufacturer via CorporateEntity name. Returns slug or None."""
        return self._entity_to_slug.get(name.lower())

    def resolve_or_create(self, name: str, *, trade_name: str = "") -> str:
        """Look up or auto-create a manufacturer, returning its slug.

        On miss, creates a Manufacturer row and updates internal caches so
        subsequent calls with the same name won't create duplicates.
        """
        from apps.catalog.models import Manufacturer

        slug = self._name_to_slug.get(name.lower())
        if slug:
            return slug

        slug = generate_unique_slug(name, self._slugs)
        Manufacturer.objects.create(
            name=name,
            slug=slug,
            trade_name=trade_name,
        )
        self._name_to_slug[name.lower()] = slug
        if trade_name:
            self._name_to_slug[trade_name.lower()] = slug
        return slug
