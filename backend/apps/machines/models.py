"""Data models for the pinball machine database.

Two-layer architecture:
- Layer 1 (provenance): Source + Claim — a stream of per-field facts from multiple sources.
- Layer 2 (resolved): PinballModel — a materialized view derived by merging claims.
"""

from __future__ import annotations

from django.db import models, transaction
from django.utils.text import slugify


class Source(models.Model):
    """A data origin: a database, a book, The Flip's editorial team, etc."""

    class SourceType(models.TextChoices):
        DATABASE = "database", "Database"
        BOOK = "book", "Book"
        EDITORIAL = "editorial", "Editorial"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.OTHER
    )
    priority = models.PositiveSmallIntegerField(
        default=0,
        help_text="Higher wins conflicts. Editorial sources should get the highest priority.",
    )
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-priority", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "source"
        super().save(*args, **kwargs)


class ClaimManager(models.Manager):
    def assert_claim(
        self,
        model: PinballModel,
        source: Source,
        field_name: str,
        value,
        citation: str = "",
    ) -> Claim:
        """Create a claim, deactivating any existing active claim for the same field+source.

        This is the only sanctioned write path for claims in production code.
        Runs in a transaction to ensure the old claim is deactivated atomically.
        """
        with transaction.atomic():
            self.filter(
                model=model,
                source=source,
                field_name=field_name,
                is_active=True,
            ).update(is_active=False)

            return self.create(
                model=model,
                source=source,
                field_name=field_name,
                value=value,
                citation=citation,
            )


class Claim(models.Model):
    """A single fact asserted by a single source about a single pinball model."""

    model = models.ForeignKey(
        "PinballModel",
        on_delete=models.CASCADE,
        related_name="claims",
    )
    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        related_name="claims",
    )
    field_name = models.CharField(max_length=100)
    value = models.JSONField()
    citation = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ClaimManager()

    class Meta:
        indexes = [
            models.Index(fields=["model", "field_name"]),
            models.Index(fields=["source", "model"]),
            models.Index(fields=["field_name", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "source", "field_name"],
                condition=models.Q(is_active=True),
                name="unique_active_claim_per_source_field",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source.name}: {self.model.name}.{self.field_name}"


class Manufacturer(models.Model):
    """A pinball machine manufacturer."""

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    trade_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Brand name if different (e.g., "Bally" for Midway Manufacturing)',
    )
    ipdb_manufacturer_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="IPDB's ManufacturerId for cross-referencing",
    )
    opdb_manufacturer_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="OPDB's manufacturer_id for cross-referencing",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        if self.trade_name and self.trade_name != self.name:
            return f"{self.trade_name} ({self.name})"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.trade_name or self.name) or "manufacturer"
            slug = base
            counter = 2
            while Manufacturer.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class PinballModel(models.Model):
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

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
            # Disambiguate: star-trek-bally-1979
            parts = [self.name]
            if self.manufacturer:
                parts.append(self.manufacturer.trade_name or self.manufacturer.name)
            if self.year:
                parts.append(str(self.year))
            base = slugify(" ".join(parts)) or "model"
            slug = base
            counter = 2
            while PinballModel.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Person(models.Model):
    """A person involved in pinball design (designer, artist, etc.)."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "people"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "person"
            slug = base
            counter = 2
            while Person.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class DesignCredit(models.Model):
    """Links a person to a pinball model with a specific role."""

    class Role(models.TextChoices):
        CONCEPT = "concept", "Concept"
        DESIGN = "design", "Design"
        ART = "art", "Art"
        MECHANICS = "mechanics", "Mechanics"
        MUSIC = "music", "Music"
        SOUND = "sound", "Sound"
        SOFTWARE = "software", "Software"
        ANIMATION = "animation", "Dots/Animation"
        OTHER = "other", "Other"

    model = models.ForeignKey(
        PinballModel,
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
                name="unique_credit_per_model_person_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person.name} — {self.get_role_display()} on {self.model.name}"
