"""Catalog models — pinball machines, manufacturers, groups, and people.

The catalog represents the resolved/materialized view of each entity.
Field values are derived by resolving claims from the provenance layer.
"""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from apps.core.models import TimeStampedModel, unique_slug


# ---------------------------------------------------------------------------
# Manufacturer
# ---------------------------------------------------------------------------


class Manufacturer(TimeStampedModel):
    """A pinball machine brand (user-facing grouping).

    Corporate incarnations are tracked separately in ManufacturerEntity.
    For example, "Gottlieb" is one Manufacturer with four ManufacturerEntity
    records spanning different ownership eras.
    """

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    trade_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Brand name if different (e.g., "Bally" for Midway Manufacturing)',
    )
    opdb_manufacturer_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="OPDB's manufacturer_id for cross-referencing",
    )
    wikidata_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Wikidata QID, e.g. Q180268",
    )
    description = models.TextField(blank=True)
    founded_year = models.IntegerField(null=True, blank=True)
    dissolved_year = models.IntegerField(null=True, blank=True)
    country = models.CharField(max_length=200, null=True, blank=True)
    headquarters = models.CharField(max_length=200, null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
    website = models.URLField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        if self.trade_name and self.trade_name != self.name:
            return f"{self.trade_name} ({self.name})"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.trade_name or self.name, "manufacturer")
        super().save(*args, **kwargs)


class ManufacturerEntity(TimeStampedModel):
    """A specific corporate incarnation of a manufacturer brand.

    IPDB tracks corporate entities (e.g., four separate entries for Gottlieb
    across its ownership eras). Each entity maps to one brand-level Manufacturer.
    """

    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.CASCADE,
        related_name="entities",
    )
    name = models.CharField(
        max_length=300,
        help_text='Full corporate name, e.g., "D. Gottlieb & Company"',
    )
    ipdb_manufacturer_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="IPDB's ManufacturerId for cross-referencing",
    )
    years_active = models.CharField(
        max_length=50,
        blank=True,
        help_text='Operating period, e.g., "1931-1977"',
    )

    class Meta:
        ordering = ["manufacturer", "years_active"]
        verbose_name = "manufacturer entity"
        verbose_name_plural = "manufacturer entities"

    def __str__(self) -> str:
        if self.years_active:
            return f"{self.name} ({self.years_active})"
        return self.name


# ---------------------------------------------------------------------------
# MachineGroup
# ---------------------------------------------------------------------------


class MachineGroup(TimeStampedModel):
    """A franchise/title grouping of related machine models.

    OPDB defines groups (e.g., "Medieval Madness" spans the 1997 original,
    the 2015 remake, and LE/SE variants). Like Manufacturer, this is a direct
    reference entity — no source contests the group's identity itself.
    Assignment of machine models to groups goes through the claims system.
    """

    opdb_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="OPDB group ID",
        help_text='OPDB group identifier, e.g., "G5pe4"',
    )
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    short_name = models.CharField(
        max_length=50,
        blank=True,
        help_text='Common abbreviation, e.g., "MM" for Medieval Madness',
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        if self.short_name:
            return f"{self.name} ({self.short_name})"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, "group")
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# MachineModel
# ---------------------------------------------------------------------------


class MachineModel(TimeStampedModel):
    """A pinball machine title/design — the resolved/materialized view.

    Fields are derived from resolving claims. The resolution logic picks the
    winning claim per field (highest priority source, most recent if tied).
    """

    class MachineType(models.TextChoices):
        PM = "PM", "Pure Mechanical"
        EM = "EM", "Electromechanical"
        SS = "SS", "Solid State"

    class DisplayType(models.TextChoices):
        REELS = "reels", "Score Reels"
        LIGHTS = "lights", "Backglass Lights"
        ALPHA = "alpha", "Alpha-Numeric"
        DMD = "dmd", "Dot Matrix Display"
        CGA = "cga", "CGA (Color Graphics)"
        LCD = "lcd", "LCD Screen"

    # Identity
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)

    # Cross-reference IDs
    ipdb_id = models.PositiveIntegerField(
        unique=True, null=True, blank=True, verbose_name="IPDB ID"
    )
    opdb_id = models.CharField(
        max_length=50, unique=True, null=True, blank=True, verbose_name="OPDB ID"
    )
    pinside_id = models.PositiveIntegerField(
        unique=True, null=True, blank=True, verbose_name="Pinside ID"
    )

    # Hierarchy
    group = models.ForeignKey(
        MachineGroup,
        on_delete=models.SET_NULL,
        related_name="machine_models",
        null=True,
        blank=True,
        help_text="Franchise/title grouping (resolved from claims).",
    )
    alias_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="aliases",
        null=True,
        blank=True,
        help_text="Parent machine model if this is a cosmetic/LE variant.",
    )

    # Core filterable fields
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        related_name="models",
        null=True,
        blank=True,
    )
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    month = models.PositiveSmallIntegerField(null=True, blank=True)
    machine_type = models.CharField(
        max_length=2, choices=MachineType.choices, blank=True
    )
    display_type = models.CharField(
        max_length=10, choices=DisplayType.choices, blank=True
    )
    player_count = models.PositiveSmallIntegerField(null=True, blank=True)
    theme = models.CharField(max_length=300, blank=True)
    production_quantity = models.CharField(max_length=100, blank=True)
    mpu = models.CharField(
        max_length=200, blank=True, verbose_name="MPU", help_text="Electronic system"
    )
    flipper_count = models.PositiveSmallIntegerField(null=True, blank=True)

    # Ratings
    ipdb_rating = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    pinside_rating = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )

    # Museum content
    educational_text = models.TextField(blank=True)
    sources_notes = models.TextField(blank=True)

    # Catch-all for fields without dedicated columns
    extra_data = models.JSONField(default=dict, blank=True)

    # Reverse access to provenance claims for this model.
    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["manufacturer", "year"]),
            models.Index(fields=["machine_type", "year"]),
            models.Index(fields=["display_type"]),
        ]

    def __str__(self) -> str:
        parts = [self.name]
        if self.manufacturer:
            parts.append(f"({self.manufacturer})")
        if self.year:
            parts.append(f"[{self.year}]")
        return " ".join(parts)

    def save(self, *args, **kwargs):
        if not self.slug:
            parts = [self.name]
            if self.manufacturer:
                parts.append(self.manufacturer.trade_name or self.manufacturer.name)
            if self.year:
                parts.append(str(self.year))
            self.slug = unique_slug(self, " ".join(parts), "model")
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Person / DesignCredit
# ---------------------------------------------------------------------------


class Person(TimeStampedModel):
    """A person involved in pinball machine design (designer, artist, etc.)."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    bio = models.TextField(blank=True)

    # Wikidata cross-reference — direct field, not a claim
    wikidata_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Wikidata ID",
        help_text='Wikidata QID, e.g., "Q312897"',
    )

    # Birth / death dates — claimed fields, resolved from provenance
    birth_year = models.IntegerField(null=True, blank=True)
    birth_month = models.IntegerField(null=True, blank=True)
    birth_day = models.IntegerField(null=True, blank=True)
    death_year = models.IntegerField(null=True, blank=True)
    death_month = models.IntegerField(null=True, blank=True)
    death_day = models.IntegerField(null=True, blank=True)

    # Biography context — claimed fields, resolved from provenance
    birth_place = models.CharField(max_length=200, null=True, blank=True)
    nationality = models.CharField(max_length=200, null=True, blank=True)
    photo_url = models.URLField(null=True, blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "people"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, "person")
        super().save(*args, **kwargs)


class DesignCredit(TimeStampedModel):
    """Links a person to a machine model with a specific role."""

    class Role(models.TextChoices):
        CONCEPT = "concept", "Concept"
        DESIGN = "design", "Design"
        ART = "art", "Art"
        MECHANICS = "mechanics", "Mechanics"
        MUSIC = "music", "Music"
        SOUND = "sound", "Sound"
        VOICE = "voice", "Voice"
        SOFTWARE = "software", "Software"
        ANIMATION = "animation", "Dots/Animation"
        OTHER = "other", "Other"

    model = models.ForeignKey(
        MachineModel,
        on_delete=models.CASCADE,
        related_name="credits",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="credits",
    )
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        ordering = ["role", "person__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "person", "role"],
                name="catalog_unique_credit_per_model_person_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person.name} — {self.get_role_display()} on {self.model.name}"


# ---------------------------------------------------------------------------
# Award / AwardRecipient
# ---------------------------------------------------------------------------


class Award(TimeStampedModel):
    """A pinball industry award (e.g., Hall of Fame, Designer of the Year).

    Fields are claim-controlled — resolved from the provenance layer.
    Recipients are managed as relationship claims on this entity.
    """

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    image_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of absolute URLs to images of this award.",
    )

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, "award")
        super().save(*args, **kwargs)


class AwardRecipient(TimeStampedModel):
    """Materialized view of a recipient relationship claim on an Award.

    The source of truth is relationship claims (field_name="recipient",
    claim_key="recipient|person:<slug>|year:<year>") on the parent Award.
    This table is populated by the resolution layer.
    """

    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="award_recipients",
    )
    year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Year the award was given (null if unknown).",
    )

    class Meta:
        ordering = [models.F("year").desc(nulls_last=True), "award__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["award", "person", "year"],
                name="catalog_unique_award_recipient",
            ),
        ]

    def __str__(self) -> str:
        year_str = str(self.year) if self.year else "unknown year"
        return f"{self.person.name} — {self.award.name} ({year_str})"
