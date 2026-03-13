"""Unit tests for OPDB relationship classification.

These tests exercise the extracted classification logic with synthetic
OpdbRecord instances — no database required.
"""

from apps.catalog.ingestion.opdb.records import OpdbRecord
from apps.catalog.ingestion.opdb.relationships import (
    classify_alias_relationship,
    pick_default_alias,
)


def _alias(opdb_id: str, name: str = "Test", features: list | None = None, **kw):
    """Shorthand for creating an OpdbRecord alias."""
    return OpdbRecord(
        opdb_id=opdb_id,
        name=name,
        is_alias=True,
        features=features or [],
        **kw,
    )


# --- pick_default_alias ---


class TestPickDefaultAlias:
    def test_premium_wins_over_le(self):
        aliases = [
            _alias("G1-M1-ALE", "LE", features=["Limited edition"]),
            _alias("G1-M1-APrem", "Premium", features=["Premium edition"]),
        ]
        chosen, issues = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-APrem"
        assert not issues

    def test_pro_wins_over_le(self):
        aliases = [
            _alias("G1-M1-ALE", "LE", features=["Limited edition"]),
            _alias("G1-M1-APro", "Pro", features=["Pro edition"]),
        ]
        chosen, issues = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-APro"
        assert not issues

    def test_le_preferred_over_ce(self):
        aliases = [
            _alias("G1-M1-ACE", "CE", features=["Collector's edition"]),
            _alias("G1-M1-ALE", "LE", features=["Limited edition"]),
        ]
        chosen, issues = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-ALE"
        assert not issues

    def test_platinum_preferred_over_ce(self):
        aliases = [
            _alias("G1-M1-ACE", "CE", features=["Collector's edition"]),
            _alias("G1-M1-APE", "PE", features=["Platinum edition"]),
        ]
        chosen, issues = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-APE"
        assert not issues

    def test_ce_never_promoted_when_alternative_exists(self):
        aliases = [
            _alias("G1-M1-ACE", "CE", features=["Collector's edition"]),
            _alias("G1-M1-AStd", "Standard", features=[]),
        ]
        chosen, issues = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-AStd"
        assert not issues

    def test_first_non_ce_when_no_premium_features(self):
        aliases = [
            _alias("G1-M1-AA", "Edition A"),
            _alias("G1-M1-AB", "Edition B"),
        ]
        chosen, issues = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-AA"

    def test_ambiguous_choice_emits_review_issue(self):
        aliases = [
            _alias("G1-M1-AA", "Edition A"),
            _alias("G1-M1-AB", "Edition B"),
        ]
        _, issues = pick_default_alias(aliases)
        assert len(issues) == 1
        assert issues[0].issue_type == "ambiguous_default_alias"
        assert "G1-M1-AA" in issues[0].context["candidates"]
        assert "G1-M1-AB" in issues[0].context["candidates"]

    def test_all_ce_emits_review_issue(self):
        aliases = [
            _alias("G1-M1-ACE1", "CE 1", features=["Collector's edition"]),
            _alias("G1-M1-ACE2", "CE 2", features=["Collector's edition"]),
        ]
        chosen, issues = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-ACE1"
        assert len(issues) == 1
        assert issues[0].issue_type == "all_collector_editions"

    def test_single_alias(self):
        aliases = [_alias("G1-M1-AOnly", "Only One")]
        chosen, issues = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-AOnly"
        assert not issues

    def test_premium_priority_order(self):
        """Premium > Pro > Limited > Platinum in priority."""
        aliases = [
            _alias("G1-M1-APlatinum", "Platinum", features=["Platinum edition"]),
            _alias("G1-M1-ALimited", "Limited", features=["Limited edition"]),
            _alias("G1-M1-APro", "Pro", features=["Pro edition"]),
            _alias("G1-M1-APremium", "Premium", features=["Premium edition"]),
        ]
        chosen, _ = pick_default_alias(aliases)
        assert chosen.opdb_id == "G1-M1-APremium"


# --- classify_alias_relationship ---


class TestClassifyAliasRelationship:
    def test_same_manufacturer_is_variant(self):
        assert classify_alias_relationship("Williams", "Williams", False) == "variant"

    def test_different_manufacturer_is_clone(self):
        assert classify_alias_relationship("Stern", "Williams", False) == "clone"

    def test_conversion_overrides_manufacturer_match(self):
        assert classify_alias_relationship("Williams", "Williams", True) == "conversion"

    def test_conversion_overrides_manufacturer_mismatch(self):
        assert classify_alias_relationship("Stern", "Williams", True) == "conversion"

    def test_empty_alias_mfr_is_variant(self):
        """If alias manufacturer is unknown, assume variant (not clone)."""
        assert classify_alias_relationship("", "Williams", False) == "variant"

    def test_empty_parent_mfr_is_variant(self):
        """If parent manufacturer is unknown, assume variant (not clone)."""
        assert classify_alias_relationship("Williams", "", False) == "variant"

    def test_both_empty_is_variant(self):
        assert classify_alias_relationship("", "", False) == "variant"

    def test_case_sensitive_mfr_comparison(self):
        """Manufacturer comparison is case-sensitive (matches source data)."""
        assert classify_alias_relationship("williams", "Williams", False) == "clone"
