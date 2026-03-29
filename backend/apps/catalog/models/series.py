"""Franchise and Series models — title-grouping entities."""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from apps.core.models import (
    LinkableModel,
    MarkdownField,
    SluggedModel,
    TimeStampedModel,
    slug_not_blank,
)
from apps.core.validators import validate_no_mojibake

__all__ = ["Franchise", "Series"]


class Franchise(SluggedModel, LinkableModel, TimeStampedModel):
    """An IP grouping that spans manufacturers and eras.

    e.g., Indiana Jones, Star Trek. Most Titles do not belong to a Franchise.
    """

    link_url_pattern = "/franchises/{slug}"

    name = models.CharField(
        max_length=200, validators=[validate_no_mojibake], unique=True
    )
    description = MarkdownField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class Series(SluggedModel, LinkableModel, TimeStampedModel):
    """A manually-curated grouping of related Titles sharing a thematic lineage.

    e.g., the "Eight Ball" series spans Eight Ball, Eight Ball Deluxe, and
    Eight Ball Champ. Series are sparse — most Titles belong to none. They can
    span multiple manufacturers. No data ingest populates them; they are
    maintained by curators via the admin or seed data.
    """

    link_url_pattern = "/series/{slug}"

    name = models.CharField(max_length=200, validators=[validate_no_mojibake])
    description = MarkdownField(blank=True)
    titles = models.ManyToManyField(
        "Title",
        blank=True,
        related_name="series",
    )

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "series"
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name
