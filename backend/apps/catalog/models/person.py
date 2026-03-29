"""Person and Credit models."""

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

__all__ = ["Person", "PersonAlias", "Credit"]


class Person(SluggedModel, LinkableModel, TimeStampedModel):
    """A person involved in pinball machine design (designer, artist, etc.)."""

    link_url_pattern = "/people/{slug}"

    name = models.CharField(max_length=200, validators=[validate_no_mojibake])
    description = MarkdownField(blank=True)

    # Wikidata cross-reference — direct field, not a claim
    wikidata_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Wikidata ID",
        help_text='Wikidata QID, e.g., "Q312897"',
        validators=[
            RegexValidator(
                r"^Q\d+$",
                message="Wikidata ID must be Q followed by digits (e.g. Q312897).",
            )
        ],
    )

    # Birth / death dates — claimed fields, resolved from provenance
    birth_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1800), MaxValueValidator(2100)],
    )
    birth_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    birth_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
    death_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1800), MaxValueValidator(2100)],
    )
    death_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    death_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )

    # Biography context — claimed fields, resolved from provenance
    birth_place = models.CharField(
        max_length=200, null=True, blank=True, validators=[validate_no_mojibake]
    )
    nationality = models.CharField(
        max_length=200, null=True, blank=True, validators=[validate_no_mojibake]
    )
    photo_url = models.URLField(null=True, blank=True)

    # Free-form staging area for source-specific data that doesn't have a
    # dedicated column yet (e.g. fandom.bio). Claims provide provenance
    # but no validation is applied. Promote keys to real fields when needed.
    extra_data = models.JSONField(default=dict, blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "people"
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class PersonAlias(AliasBase):
    """An alternate name for a Person, used to match alternative spellings from
    external sources (e.g. "Keith Johnson" → "Keith P. Johnson").
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="aliases")

    class Meta(AliasBase.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("value"),
                name="catalog_unique_person_alias_lower",
            ),
        ]


class Credit(TimeStampedModel):
    """Links a person to a machine model or series with a specific role."""

    model = models.ForeignKey(
        "MachineModel",
        on_delete=models.CASCADE,
        related_name="credits",
        null=True,
        blank=True,
    )
    series = models.ForeignKey(
        "Series",
        on_delete=models.CASCADE,
        related_name="credits",
        null=True,
        blank=True,
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="credits",
    )
    role = models.ForeignKey(
        "CreditRole",
        on_delete=models.PROTECT,
        related_name="credits",
    )

    class Meta:
        ordering = ["role__display_order", "person__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "person", "role"],
                name="catalog_unique_credit_per_model_person_role",
                condition=models.Q(model__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["series", "person", "role"],
                name="catalog_unique_credit_per_series_person_role",
                condition=models.Q(series__isnull=False),
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(model__isnull=False, series__isnull=True)
                    | models.Q(model__isnull=True, series__isnull=False)
                ),
                name="catalog_credit_model_xor_series",
            ),
        ]

    def __str__(self) -> str:
        target = self.model.name if self.model else self.series.name
        return f"{self.person.name} — {self.role.name} on {target}"
