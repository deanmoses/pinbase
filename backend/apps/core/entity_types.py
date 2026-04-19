"""Public entity_type → catalog model class resolution.

Every catalog entity declares a hyphenated canonical public identifier via
``CatalogModel.entity_type``. This module is the single adapter from that
public string to the concrete model class. Callers that need Django's
concatenated ``_meta.model_name`` or a ContentType use the returned class
directly.

Unknown (or concatenated / Django-internal) entity_type strings raise
``ValueError``; callers translate to HTTP 404.
"""

from __future__ import annotations

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

from apps.core.models import CatalogModel

_ENTITY_TYPE_MAP: dict[str, type[CatalogModel]] | None = None


def _build_map() -> dict[str, type[CatalogModel]]:
    # Ensure all apps are loaded so every CatalogModel subclass is imported.
    apps.check_apps_ready()
    result: dict[str, type[CatalogModel]] = {}

    def walk(cls: type[CatalogModel]) -> None:
        for subclass in cls.__subclasses__():
            walk(subclass)
            meta = getattr(subclass, "_meta", None)
            if meta is None or meta.abstract:
                continue
            key = subclass.entity_type
            if key in result:
                raise ImproperlyConfigured(
                    f"Duplicate entity_type {key!r}: "
                    f"{result[key].__name__} and {subclass.__name__}"
                )
            result[key] = subclass

    walk(CatalogModel)
    return result


def get_catalog_model(entity_type: str) -> type[CatalogModel]:
    """Return the catalog model class for a canonical entity_type string.

    Raises ``ValueError`` if the entity_type is unknown — including
    Django-internal concatenated forms like ``'corporateentity'`` or
    ``'machinemodel'``.
    """
    global _ENTITY_TYPE_MAP
    if _ENTITY_TYPE_MAP is None:
        _ENTITY_TYPE_MAP = _build_map()
    try:
        return _ENTITY_TYPE_MAP[entity_type]
    except KeyError:
        raise ValueError(f"Unknown entity type: {entity_type}") from None
