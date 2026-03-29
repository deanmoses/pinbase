"""Title and TitleAbbreviation models."""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import (
    LinkableModel,
    MarkdownField,
    SluggedModel,
    TimeStampedModel,
    slug_not_blank,
)
from apps.core.validators import validate_no_mojibake

__all__ = ["Title", "TitleAbbreviation"]


class Title(SluggedModel, LinkableModel, TimeStampedModel):
    """The canonical identity of a pinball game, independent of edition or variant.

    OPDB calls this a "group" in its JSON, but we use "Title" as it is the
    natural pinball-world term (e.g., "Medieval Madness" spans the 1997
    original, the 2015 remake, and LE/SE variants). Title fields (name, description, franchise) and
    abbreviations are resolved from claims, just like MachineModel and
    Manufacturer.
    """

    link_url_pattern = "/titles/{slug}"

    opdb_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="OPDB group ID",
        help_text='OPDB group ID (e.g., "G5pe4"). Null for titles without an OPDB group.',
        validators=[validate_no_mojibake],
    )
    name = models.CharField(max_length=300, validators=[validate_no_mojibake])
    slug = models.SlugField(max_length=300, unique=True)
    description = MarkdownField(blank=True)
    franchise = models.ForeignKey(
        "Franchise",
        on_delete=models.SET_NULL,
        related_name="titles",
        null=True,
        blank=True,
    )
    fandom_page_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Fandom wiki page ID for deep-linking.",
        validators=[MinValueValidator(1)],
    )
    needs_review = models.BooleanField(
        default=False,
        help_text="Title was auto-generated and may need human review.",
    )
    needs_review_notes = models.TextField(
        blank=True,
        help_text="Context for reviewers about why this title needs attention.",
        validators=[validate_no_mojibake],
    )

    # Reverse access to provenance claims for this title.
    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class TitleAbbreviation(TimeStampedModel):
    """A common abbreviation for a Title, e.g. "MM" for Medieval Madness.

    Materialized from provenance claims; each abbreviation is individually
    tracked with source attribution.
    """

    title = models.ForeignKey(
        Title, on_delete=models.CASCADE, related_name="abbreviations"
    )
    value = models.CharField(max_length=50)

    class Meta:
        ordering = ["value"]
        unique_together = [("title", "value")]

    def __str__(self) -> str:
        return self.value
