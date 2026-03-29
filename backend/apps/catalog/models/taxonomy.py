"""Taxonomy lookup models — technology, display, cabinet, game format, etc."""

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

__all__ = [
    "TechnologyGeneration",
    "TechnologySubgeneration",
    "DisplayType",
    "DisplaySubtype",
    "Cabinet",
    "GameFormat",
    "RewardType",
    "RewardTypeAlias",
    "Tag",
    "CreditRole",
]


class TechnologyGeneration(SluggedModel, LinkableModel, TimeStampedModel):
    """A major technological era: Pure Mechanical, Electromechanical, Solid State.

    Name and display_order are claim-controlled; description is direct editorial.
    """

    link_url_pattern = "/technology-generations/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class TechnologySubgeneration(SluggedModel, LinkableModel, TimeStampedModel):
    """A subdivision within a TechnologyGeneration.

    e.g., Solid State → Discrete Logic, Integrated (MPU), PC-Based.
    """

    link_url_pattern = "/technology-subgenerations/{slug}"

    name = models.CharField(max_length=200, validators=[validate_no_mojibake])
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)
    technology_generation = models.ForeignKey(
        TechnologyGeneration,
        on_delete=models.CASCADE,
        related_name="subgenerations",
    )

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class DisplayType(SluggedModel, LinkableModel, TimeStampedModel):
    """A display technology category: Score Reels, DMD, LCD, etc.

    Replaces the old DisplayType enum.
    """

    link_url_pattern = "/display-types/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class DisplaySubtype(SluggedModel, LinkableModel, TimeStampedModel):
    """A subdivision within a DisplayType.

    e.g., LCD → Standard LCD, HD LCD.
    """

    link_url_pattern = "/display-subtypes/{slug}"

    name = models.CharField(max_length=200, validators=[validate_no_mojibake])
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)
    display_type = models.ForeignKey(
        DisplayType,
        on_delete=models.CASCADE,
        related_name="subtypes",
    )

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class Cabinet(SluggedModel, LinkableModel, TimeStampedModel):
    """Physical cabinet form factor: Floor, Tabletop, Countertop, Cocktail."""

    link_url_pattern = "/cabinets/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class GameFormat(SluggedModel, LinkableModel, TimeStampedModel):
    """Game format: Pinball, Bagatelle, Shuffle Alley, Pitch-and-Bat."""

    link_url_pattern = "/game-formats/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class RewardType(SluggedModel, LinkableModel, TimeStampedModel):
    """A pinball reward mechanism: replay, add-a-ball, free-play, etc.

    Reward types are the payoff mechanic for achieving a goal, distinct from
    gameplay features (the mechanisms used to earn that payoff).
    """

    link_url_pattern = "/reward-types/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class RewardTypeAlias(AliasBase):
    """An alternate name for a RewardType, used for matching/search."""

    reward_type = models.ForeignKey(
        RewardType, on_delete=models.CASCADE, related_name="aliases"
    )

    class Meta(AliasBase.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("value"),
                name="catalog_unique_reward_type_alias_lower",
            ),
        ]


class Tag(SluggedModel, LinkableModel, TimeStampedModel):
    """A classification tag: Home Use, Prototype, Widebody, Remake, etc.

    Linked to MachineModel via M2M relationship claims.
    """

    link_url_pattern = "/tags/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name


class CreditRole(SluggedModel, LinkableModel, TimeStampedModel):
    """A credit role category: Design, Art, Software, etc."""

    link_url_pattern = "/credit-roles/{slug}"

    name = models.CharField(
        max_length=200, unique=True, validators=[validate_no_mojibake]
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    description = MarkdownField(blank=True)

    claims = GenericRelation("provenance.Claim")

    class Meta:
        ordering = ["display_order"]
        constraints = [slug_not_blank()]

    def __str__(self) -> str:
        return self.name
