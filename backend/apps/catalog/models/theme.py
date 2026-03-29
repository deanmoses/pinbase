"""Theme and ThemeAlias models."""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import (
    AliasBase,
    LinkableModel,
    MarkdownField,
    SluggedModel,
    TimeStampedModel,
    slug_not_blank,
)
from apps.core.validators import validate_no_mojibake

__all__ = ["Theme", "ThemeAlias"]


class Theme(SluggedModel, LinkableModel, TimeStampedModel):
    """A thematic tag for pinball machines (e.g., Sports, Horror, Licensed).

    Supports a DAG hierarchy via the ``parents`` M2M (structural, not
    claim-controlled).  The MachineModel-Theme relationship is materialized
    from relationship claims.
    """

    link_url_pattern = "/themes/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    description = MarkdownField(blank=True)
    parents = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="children",
        blank=True,
        help_text="Parent themes in the hierarchy (materialized from relationship claims).",
    )

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class ThemeAlias(AliasBase):
    """An alternate name for a Theme, used for matching/search."""

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="aliases")

    class Meta(AliasBase.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("value"),
                name="catalog_unique_theme_alias_lower",
            ),
        ]
