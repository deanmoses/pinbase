"""Provenance layer: Source + Claim.

A Source is a named origin of data (external database, book, editorial team).
A Claim is a single fact asserted by a Source or User about any catalog entity.
Claims use a GenericForeignKey so they can target any model (MachineModel,
Manufacturer, Person, etc.).
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction

from apps.core.models import TimeStampedModel, unique_slug


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
        subject,
        field_name: str,
        value,
        citation: str = "",
        *,
        source: Source | None = None,
        user=None,
    ) -> "Claim":
        """Create a claim, deactivating any existing active claim for the same field+author.

        ``subject`` can be any model instance (MachineModel, Manufacturer, Person, …).
        Exactly one of ``source`` or ``user`` must be provided.
        Runs in a transaction to ensure the old claim is deactivated atomically.
        """
        if (source is None) == (user is None):
            raise ValueError("Exactly one of source or user must be provided.")
        ct = ContentType.objects.get_for_model(subject)
        with transaction.atomic():
            self.filter(
                content_type=ct,
                object_id=subject.pk,
                source=source,
                user=user,
                field_name=field_name,
                is_active=True,
            ).update(is_active=False)

            return self.create(
                content_type=ct,
                object_id=subject.pk,
                source=source,
                user=user,
                field_name=field_name,
                value=value,
                citation=citation,
            )

    def bulk_assert_claims(
        self,
        source: Source,
        pending_claims: list["Claim"],
    ) -> dict[str, int]:
        """Bulk-assert claims for a source. Only writes what changed.

        Compares pending claims against existing active claims from the same
        source. Unchanged claims are skipped, changed claims are superseded
        (deactivated), and new/changed claims are created in bulk.

        Idempotent: running the same ingest twice writes zero rows the second time.

        ``pending_claims`` is a list of **unsaved** Claim objects with
        ``content_type_id``, ``object_id``, ``field_name``, ``value``, and
        ``citation`` set. The ``source`` FK is set here.
        """
        # 1. Deduplicate: last-write-wins per (content_type_id, object_id, field_name),
        #    matching assert_claim() semantics where later calls overwrite.
        seen: dict[tuple[int, int, str], Claim] = {}
        for claim in pending_claims:
            claim.source = source
            seen[(claim.content_type_id, claim.object_id, claim.field_name)] = claim
        deduped = list(seen.values())
        duplicates_removed = len(pending_claims) - len(deduped)

        # 2. Fetch existing active claims from this source.
        existing: dict[tuple[int, int, str], Claim] = {}
        for claim in self.filter(source=source, is_active=True):
            existing[(claim.content_type_id, claim.object_id, claim.field_name)] = claim

        # 3. Diff: skip unchanged, collect superseded + new.
        to_deactivate_ids: list[int] = []
        to_create: list[Claim] = []
        for new_claim in deduped:
            key = (new_claim.content_type_id, new_claim.object_id, new_claim.field_name)
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
    """A single fact asserted by a Source or User about any catalog entity.

    Uses a GenericForeignKey (``subject``) so claims can target any model:
    MachineModel, Manufacturer, Person, etc.

    Exactly one of ``source`` or ``user`` must be set — enforced by a
    CheckConstraint and by ClaimManager.assert_claim().
    """

    objects = ClaimManager()

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    subject = GenericForeignKey("content_type", "object_id")

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

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id", "field_name"]),
            models.Index(fields=["source", "content_type", "object_id"]),
            models.Index(fields=["user", "content_type", "object_id"]),
            models.Index(fields=["field_name", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(source__isnull=False, user__isnull=True)
                    | models.Q(source__isnull=True, user__isnull=False)
                ),
                name="provenance_claim_source_xor_user",
            ),
            models.UniqueConstraint(
                fields=["content_type", "object_id", "source", "field_name"],
                condition=models.Q(is_active=True, source__isnull=False),
                name="provenance_unique_active_claim_per_source_field",
            ),
            models.UniqueConstraint(
                fields=["content_type", "object_id", "user", "field_name"],
                condition=models.Q(is_active=True, user__isnull=False),
                name="provenance_unique_active_claim_per_user_field",
            ),
        ]

    def __str__(self) -> str:
        author = self.source.name if self.source_id else self.user.username
        return f"{author}: {self.subject}.{self.field_name}"
