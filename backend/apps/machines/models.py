"""Machine catalog models.

Two-layer architecture:
- Layer 1 (provenance): Source + Claim — a stream of per-field facts from multiple sources.
- Layer 2 (resolved): MachineModel — a materialized view derived by merging claims.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models, transaction

from apps.core.models import TimeStampedModel, unique_slug


# ---------------------------------------------------------------------------
# Source / Claim (provenance layer)
# ---------------------------------------------------------------------------


class Source(TimeStampedModel):
    """A data origin point (external database, book, editorial team, etc.)."""

    class SourceType(models.TextChoices):
        DATABASE = "database", "Database"
        BOOK = "book", "Book"
        EDITORIAL = "editorial", "Editorial"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.DATABASE
    )
    priority = models.PositiveSmallIntegerField(
        default=0,
        help_text="Higher priority wins when claims conflict.",
    )
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-priority", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, "source")
        super().save(*args, **kwargs)


class ClaimManager(models.Manager):
    def assert_claim(
        self,
        model: MachineModel,
        field_name: str,
        value,
        citation: str = "",
        *,
        source: Source | None = None,
        user=None,
    ) -> Claim:
        """Create a claim, deactivating any existing active claim for the same field+author.

        Exactly one of ``source`` or ``user`` must be provided.
        This is the only sanctioned write path for claims in production code.
        Runs in a transaction to ensure the old claim is deactivated atomically.
        """
        if (source is None) == (user is None):
            raise ValueError("Exactly one of source or user must be provided.")
        with transaction.atomic():
            self.filter(
                model=model,
                source=source,
                user=user,
                field_name=field_name,
                is_active=True,
            ).update(is_active=False)

            return self.create(
                model=model,
                source=source,
                user=user,
                field_name=field_name,
                value=value,
                citation=citation,
            )

    def bulk_assert_claims(
        self,
        source: Source,
        pending_claims: list[Claim],
    ) -> dict[str, int]:
        """Bulk-assert claims for a source. Only writes what changed.

        Compares pending claims against existing active claims from the same
        source. Unchanged claims are skipped, changed claims are superseded
        (deactivated), and new/changed claims are created in bulk.

        Idempotent: running the same ingest twice writes zero rows the second
        time.

        ``pending_claims`` is a list of **unsaved** Claim objects with
        ``model_id``, ``field_name``, ``value``, and ``citation`` set.
        The ``source`` FK is set here.
        """
        # 1. Deduplicate: last-write-wins per (model_id, field_name),
        #    matching assert_claim() semantics where later calls overwrite.
        seen: dict[tuple[int, str], Claim] = {}
        for claim in pending_claims:
            claim.source = source
            seen[(claim.model_id, claim.field_name)] = claim
        deduped = list(seen.values())
        duplicates_removed = len(pending_claims) - len(deduped)

        # 2. Fetch existing active claims from this source.
        existing: dict[tuple[int, str], Claim] = {}
        for claim in self.filter(source=source, is_active=True):
            existing[(claim.model_id, claim.field_name)] = claim

        # 3. Diff: skip unchanged, collect superseded + new.
        to_deactivate_ids: list[int] = []
        to_create: list[Claim] = []
        for new_claim in deduped:
            key = (new_claim.model_id, new_claim.field_name)
            old = existing.get(key)
            if (
                old
                and old.value == new_claim.value
                and old.citation == new_claim.citation
            ):
                continue  # Already correct
            if old:
                to_deactivate_ids.append(old.pk)
            to_create.append(new_claim)

        # 4. Apply delta atomically.
        with transaction.atomic():
            if to_deactivate_ids:
                self.filter(pk__in=to_deactivate_ids).update(is_active=False)
            if to_create:
                self.bulk_create(to_create, batch_size=2000)

        return {
            "unchanged": len(deduped) - len(to_create),
            "created": len(to_create),
            "superseded": len(to_deactivate_ids),
            "duplicates_removed": duplicates_removed,
        }


class Claim(models.Model):
    """A single fact asserted by a source or a user about a single machine model.

    Exactly one of ``source`` or ``user`` must be set — enforced by a CheckConstraint
    and by ClaimManager.assert_claim().
    """

    model = models.ForeignKey(
        "MachineModel",
        on_delete=models.CASCADE,
        related_name="claims",
    )
    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        related_name="claims",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="claims",
        null=True,
        blank=True,
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
            models.Index(fields=["user", "model"]),
            models.Index(fields=["field_name", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(source__isnull=False, user__isnull=True)
                    | models.Q(source__isnull=True, user__isnull=False)
                ),
                name="claim_source_xor_user",
            ),
            models.UniqueConstraint(
                fields=["model", "source", "field_name"],
                condition=models.Q(is_active=True, source__isnull=False),
                name="unique_active_claim_per_source_field",
            ),
            models.UniqueConstraint(
                fields=["model", "user", "field_name"],
                condition=models.Q(is_active=True, user__isnull=False),
                name="unique_active_claim_per_user_field",
            ),
        ]

    def __str__(self) -> str:
        author = self.source.name if self.source_id else self.user.username
        return f"{author}: {self.model.name}.{self.field_name}"


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
                name="unique_credit_per_model_person_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person.name} — {self.get_role_display()} on {self.model.name}"
