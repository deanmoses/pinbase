"""Manufacturer and CorporateEntity models."""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
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

__all__ = [
    "Manufacturer",
    "ManufacturerAlias",
    "CorporateEntity",
    "CorporateEntityAlias",
]


class Manufacturer(SluggedModel, LinkableModel, TimeStampedModel):
    """A pinball machine brand (user-facing grouping).

    Corporate incarnations are tracked separately in ManufacturerEntity.
    For example, "Gottlieb" is one Manufacturer with four ManufacturerEntity
    records spanning different ownership eras.
    """

    link_url_pattern = "/manufacturers/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    opdb_manufacturer_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="OPDB manufacturer_id for this brand.",
        validators=[MinValueValidator(1)],
    )
    wikidata_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Wikidata QID, e.g. Q180268",
        validators=[
            RegexValidator(
                r"^Q\d+$",
                message="Wikidata ID must be Q followed by digits (e.g. Q180268).",
            )
        ],
    )
    description = MarkdownField(blank=True)
    logo_url = models.URLField(null=True, blank=True)
    website = models.URLField(blank=True)

    # Free-form staging area for source-specific data that doesn't have a
    # dedicated column yet (e.g. fandom.description). Claims provide provenance
    # but no validation is applied. Promote keys to real fields when needed.
    extra_data = models.JSONField(default=dict, blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class ManufacturerAlias(AliasBase):
    """An alternate name for a Manufacturer, used to match alternative spellings
    from external sources.
    """

    manufacturer = models.ForeignKey(
        Manufacturer, on_delete=models.CASCADE, related_name="aliases"
    )

    class Meta(AliasBase.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("value"),
                name="catalog_unique_manufacturer_alias_lower",
            ),
        ]


class CorporateEntity(SluggedModel, LinkableModel, TimeStampedModel):
    """A specific corporate incarnation of a manufacturer brand.

    IPDB tracks corporate entities (e.g., four separate entries for Gottlieb
    across its ownership eras). Each entity maps to one brand-level Manufacturer.
    """

    link_url_pattern = "/corporate-entities/{slug}"

    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.CASCADE,
        related_name="entities",
    )
    slug = models.SlugField(max_length=300, unique=True)
    description = MarkdownField(blank=True)
    name = models.CharField(
        max_length=300,
        help_text='Full corporate name, e.g., "D. Gottlieb & Company"',
        validators=[validate_no_mojibake],
    )
    ipdb_manufacturer_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="IPDB ManufacturerId for this corporate entity.",
        validators=[MinValueValidator(1)],
    )
    year_start = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Year this corporate entity was established.",
        validators=[MinValueValidator(1800), MaxValueValidator(2100)],
    )
    year_end = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Year this corporate entity ceased operations.",
        validators=[MinValueValidator(1800), MaxValueValidator(2100)],
    )

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["manufacturer", "year_start"]
        verbose_name = "corporate entity"
        verbose_name_plural = "corporate entities"
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        if self.year_start:
            end = self.year_end or "present"
            return f"{self.name} ({self.year_start}-{end})"
        return self.name


class CorporateEntityAlias(AliasBase):
    """An alternate name for a CorporateEntity, used to match alternative spellings
    from external sources.
    """

    corporate_entity = models.ForeignKey(
        CorporateEntity, on_delete=models.CASCADE, related_name="aliases"
    )

    class Meta(AliasBase.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("value"),
                name="catalog_unique_corporate_entity_alias_lower",
            ),
        ]
