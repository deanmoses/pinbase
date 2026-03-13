"""OPDB alias relationship classification.

Extracts the variant/clone/conversion classification logic from ingest_opdb
into testable functions with explicit intermediate records.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .records import OpdbRecord

# Feature labels that indicate a "default" (canonical) variant, in priority
# order. Collector's Edition is always a variant, never promoted.
_DEFAULT_FEATURES = [
    "Premium edition",
    "Pro edition",
    "Limited edition",
    "Platinum edition",
]
_VARIANT_FEATURES = ["Collector's edition"]


@dataclass
class RelationshipCandidate:
    """An explicit, inspectable record of a proposed relationship."""

    source_opdb_id: str
    target_opdb_id: str
    relationship_type: str  # "variant"
    rule_name: str
    confidence: str  # "auto" or "review"
    explanation: str


@dataclass
class ReviewIssue:
    """A case where the pipeline made a weak or ambiguous decision."""

    source_opdb_id: str
    issue_type: str
    description: str
    context: dict = field(default_factory=dict)


def pick_default_alias(
    aliases: list[OpdbRecord],
) -> tuple[OpdbRecord, list[ReviewIssue]]:
    """Pick the alias to promote to canonical model from a non-physical group.

    Heuristic priority:
    1. Alias with Premium/Pro/Limited/Platinum edition feature (first match wins)
    2. First alias that is NOT a Collector's Edition
    3. First in the list (arbitrary — models.json corrects ambiguous cases)

    Returns the chosen alias and any review issues for weak decisions.
    """
    issues: list[ReviewIssue] = []
    parent_id = aliases[0].parent_opdb_id if aliases else "?"

    # Priority 1: Known premium features.
    for label in _DEFAULT_FEATURES:
        for rec in aliases:
            if label in rec.features:
                return rec, issues

    # Priority 2: First non-Collector's Edition.
    non_ce = [r for r in aliases if not any(f in r.features for f in _VARIANT_FEATURES)]
    if non_ce:
        if len(non_ce) > 1:
            issues.append(
                ReviewIssue(
                    source_opdb_id=parent_id,
                    issue_type="ambiguous_default_alias",
                    description=(
                        f"Multiple aliases without distinguishing features; "
                        f"picked first: {non_ce[0].name}"
                    ),
                    context={"candidates": [r.opdb_id for r in non_ce]},
                )
            )
        return non_ce[0], issues

    # Fallback: all are Collector's Editions (or have no features at all).
    issues.append(
        ReviewIssue(
            source_opdb_id=parent_id,
            issue_type="all_collector_editions",
            description=(
                f"All aliases are Collector's Editions; picked first: {aliases[0].name}"
            ),
            context={"aliases": [r.opdb_id for r in aliases]},
        )
    )
    return aliases[0], issues


def classify_alias_relationship(
    alias_mfr: str,
    parent_mfr: str,
    is_conversion: bool,
) -> str:
    """Classify an alias's relationship to its parent.

    Returns one of:
    - "variant": same manufacturer, normal edition variant
    - "clone": different manufacturer (licensed reproduction)
    - "conversion": pinbase editorial marks this as a conversion
    """
    if is_conversion:
        return "conversion"
    if alias_mfr and parent_mfr and alias_mfr != parent_mfr:
        return "clone"
    return "variant"
