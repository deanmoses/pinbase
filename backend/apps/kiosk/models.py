"""Kiosk configuration models.

Kiosk configs are operational settings for kiosk-mode displays — not catalog
claims. They use plain Django models with no claims plumbing (see
docs/Provenance.md).
"""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel, field_not_blank
from apps.core.validators import validate_no_mojibake

__all__ = ["KioskConfig", "KioskConfigItem"]

IDLE_SECONDS_MIN = 10
IDLE_SECONDS_MAX = 3600


class KioskConfig(TimeStampedModel):
    """A named kiosk display configuration.

    A device "selects" a config via the ``kioskConfigId`` cookie set in the
    frontend. Multiple devices can share one config; one device shows one
    config at a time.
    """

    items: models.Manager[KioskConfigItem]

    name = models.CharField(
        max_length=80,
        unique=True,
        validators=[validate_no_mojibake],
        help_text="Admin label shown in the kiosk list (e.g. 'Lobby kiosk').",
    )
    page_heading = models.CharField(
        max_length=60,
        blank=True,
        default="",
        validators=[validate_no_mojibake],
        help_text="H1 rendered on the kiosk display. Blank to render no heading.",
    )
    idle_seconds = models.PositiveIntegerField(
        default=180,
        validators=[
            MinValueValidator(IDLE_SECONDS_MIN),
            MaxValueValidator(IDLE_SECONDS_MAX),
        ],
        help_text="Idle timeout before redirecting back to /kiosk.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            field_not_blank("name"),
            models.CheckConstraint(
                condition=models.Q(
                    idle_seconds__gte=IDLE_SECONDS_MIN,
                    idle_seconds__lte=IDLE_SECONDS_MAX,
                ),
                name="kiosk_kioskconfig_idle_seconds_range",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class KioskConfigItem(TimeStampedModel):
    """One Title slot in a KioskConfig, ordered by ``position``.

    CASCADE on the Title FK is deliberate (operational data adapts to catalog
    deletes — see plan, "Decisions → Items").
    """

    config = models.ForeignKey(
        KioskConfig,
        on_delete=models.CASCADE,
        related_name="items",
    )
    title = models.ForeignKey(
        "catalog.Title",
        on_delete=models.CASCADE,
        related_name="+",
    )
    hook = models.CharField(
        max_length=80,
        blank=True,
        validators=[validate_no_mojibake],
        help_text="Optional short caption shown alongside the title.",
    )
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["config_id", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["config", "position"],
                name="kiosk_kioskconfigitem_position_unique",
            ),
            models.UniqueConstraint(
                fields=["config", "title"],
                name="kiosk_kioskconfigitem_title_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.config.name} #{self.position}: {self.title.name}"
