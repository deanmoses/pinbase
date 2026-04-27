"""CatalogModel and AliasBase abstract bases for catalog entities."""

from __future__ import annotations

from typing import ClassVar, Self

from django.db import models

from apps.core.models import (
    CatalogManager,
    EntityStatusMixin,
    LinkableModel,
    TimeStampedModel,
)
from apps.provenance.models import ClaimControlledModel

__all__ = ["AliasBase", "CatalogModel"]


class AliasBase(TimeStampedModel):
    """Abstract base for alias lookup models.

    Alias values are stored and compared in lowercase (matching the
    UniqueConstraint(Lower("value")) that every subclass must define).
    Claims live on the *parent* object, not on the alias row itself.

    Subclasses must add:
    - A ForeignKey to the parent model (named after the parent, related_name="aliases")
    - A UniqueConstraint on Lower("value") with a table-specific name
    - ``alias_claim_field``: the claim namespace on the parent that carries
      alias values (e.g. ``"theme_alias"``). Enforced at class creation
      via ``__init_subclass__``; read by ``discover_alias_types``.
    """

    alias_claim_field: ClassVar[str]

    value = models.CharField(max_length=200)

    class Meta(TimeStampedModel.Meta):
        abstract = True
        ordering = ["value"]

    def __init_subclass__(cls, **kwargs: object) -> None:
        # NB: we can't gate on ``cls._meta.abstract`` here — Django's ModelBase
        # runs ``__init_subclass__`` with ``abstract`` still inherited as True
        # from the parent, then rewrites it to False for concrete subclasses
        # later. So this check runs for every AliasBase subclass, concrete or
        # not. That's fine: any abstract intermediate can just declare
        # ``alias_claim_field`` for its concrete descendants to inherit.
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "alias_claim_field", None):
            raise TypeError(
                f"{cls.__name__} must declare a non-empty `alias_claim_field` "
                'class attr (e.g. `alias_claim_field = "theme_alias"`)'
            )

    def __str__(self) -> str:
        return self.value


class CatalogModel(LinkableModel, EntityStatusMixin, ClaimControlledModel):
    """Abstract marker for top-level catalog entities.

    Combines URL-addressability (``LinkableModel``), claim-controlled
    lifecycle status (``EntityStatusMixin``), and claim-driven display
    fields (``ClaimControlledModel``). Used to distinguish catalog-specific
    code paths (e.g. ``ingest_pinbase``, soft-delete wire format) that must
    not widen to other ``LinkableModel`` subclasses.

    Concrete subclasses inherit all three capabilities transitively and do
    not relist them in their own bases. Each concrete subclass must still
    carry its own ``status_valid()`` constraint in ``Meta`` because Django
    does not inherit abstract-parent constraints when a concrete model
    defines its own ``Meta``.
    """

    # Re-declare ``objects`` here (originally on ``EntityStatusMixin``) so
    # ``Self`` rebinds at the catalog level. Without this, mypy resolves
    # ``model_cls.objects.active()`` (where ``model_cls: type[ModelT:
    # CatalogModel]``) by walking the type bound and binds ``Self`` to
    # ``EntityStatusMixin`` — the class where the descriptor is declared —
    # rather than ``ModelT``. Runtime is unaffected: same ``CatalogManager``
    # class, Django's ManagerDescriptor rebinds per concrete model anyway.
    # ``EntityStatusMixin.objects`` stays put so ``Location`` (which uses
    # the mixin without ``CatalogModel``) keeps its ``.active()`` queryset.
    objects: ClassVar[CatalogManager[Self]] = CatalogManager()

    class Meta:
        abstract = True
