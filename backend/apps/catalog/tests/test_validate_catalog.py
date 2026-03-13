"""Tests for the validate_catalog management command."""

import pytest
from django.core.management import call_command

from apps.catalog.models import (
    CreditRole,
    MachineModel,
    Manufacturer,
    Person,
    Theme,
    Title,
)
from apps.provenance.models import Claim, Source


@pytest.fixture
def ipdb(db):
    return Source.objects.create(name="IPDB", source_type="database", priority=10)


@pytest.fixture
def pinbase_source(db):
    return Source.objects.create(
        name="Pinbase", slug="pinbase", source_type="editorial", priority=300
    )


@pytest.fixture
def manufacturer(db):
    return Manufacturer.objects.create(name="Williams", slug="williams")


@pytest.fixture
def title(db):
    return Title.objects.create(
        name="Medieval Madness", slug="medieval-madness", opdb_id="G1234"
    )


class TestValidateCatalogClean:
    """A clean catalog should produce no errors or warnings."""

    def test_empty_catalog_no_errors(self, db, capsys):
        """Empty catalog is valid — no errors or warnings."""
        call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "error(s)" in captured.out
        assert "0 error(s)" in captured.out
        assert "0 warning(s)" in captured.out

    def test_clean_model_no_errors(self, db, manufacturer, title, capsys):
        MachineModel.objects.create(
            name="Medieval Madness",
            slug="medieval-madness-williams-1997",
            manufacturer=manufacturer,
            title=title,
            year=1997,
        )
        call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "0 error(s)" in captured.out


class TestNamelessEntities:
    def test_nameless_model_is_error(self, db, capsys):
        MachineModel.objects.create(name="", slug="empty-name")
        with pytest.raises(SystemExit, match="1"):
            call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "have no name" in captured.out

    def test_nameless_title_is_error(self, db, capsys):
        Title.objects.create(name="", slug="empty-title", opdb_id="G0000")
        with pytest.raises(SystemExit, match="1"):
            call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "title(s) have no name" in captured.out

    def test_nameless_person_is_error(self, db, capsys):
        Person.objects.create(name="", slug="empty-person")
        with pytest.raises(SystemExit, match="1"):
            call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "person(s) have no name" in captured.out


class TestConversionVariantConflict:
    def test_conversion_with_variant_of_is_error(self, db, manufacturer, capsys):
        parent = MachineModel.objects.create(
            name="Parent", slug="parent", manufacturer=manufacturer
        )
        MachineModel.objects.create(
            name="Child",
            slug="child",
            manufacturer=manufacturer,
            is_conversion=True,
            variant_of=parent,
        )
        with pytest.raises(SystemExit, match="1"):
            call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "is_conversion=True and variant_of" in captured.out


class TestVariantChains:
    def test_variant_chain_is_warning(self, db, manufacturer, capsys):
        root = MachineModel.objects.create(
            name="Root", slug="root", manufacturer=manufacturer
        )
        mid = MachineModel.objects.create(
            name="Mid", slug="mid", manufacturer=manufacturer, variant_of=root
        )
        MachineModel.objects.create(
            name="Leaf", slug="leaf", manufacturer=manufacturer, variant_of=mid
        )
        call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "variant_of chains" in captured.out
        assert "0 error(s)" in captured.out

    def test_variant_chain_fails_with_fail_on_warn(self, db, manufacturer, capsys):
        root = MachineModel.objects.create(
            name="Root", slug="root", manufacturer=manufacturer
        )
        mid = MachineModel.objects.create(
            name="Mid", slug="mid", manufacturer=manufacturer, variant_of=root
        )
        MachineModel.objects.create(
            name="Leaf", slug="leaf", manufacturer=manufacturer, variant_of=mid
        )
        with pytest.raises(SystemExit, match="1"):
            call_command("validate_catalog", "--fail-on-warn")


class TestDuplicatePersons:
    def test_duplicate_person_names_are_warning(self, db, capsys):
        Person.objects.create(name="Pat Lawlor", slug="pat-lawlor")
        Person.objects.create(name="pat lawlor", slug="pat-lawlor-2")
        call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "person name(s) appear more than once" in captured.out


class TestUnresolvedFKClaims:
    def test_unresolved_manufacturer_claim_is_warning(self, db, ipdb, capsys):
        pm = MachineModel.objects.create(name="Test", slug="test-model")
        Claim.objects.assert_claim(pm, "manufacturer", "nonexistent-mfr", source=ipdb)
        call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "unresolved manufacturer claim" in captured.out


class TestUnresolvedCreditClaims:
    def test_missing_person_in_credit_claim(self, db, ipdb, capsys):
        CreditRole.objects.create(name="Design", slug="design")
        pm = MachineModel.objects.create(name="Test", slug="test-model")
        from apps.catalog.claims import build_relationship_claim

        claim_key, value = build_relationship_claim(
            "credit", {"person_slug": "ghost-person", "role": "design"}
        )
        Claim.objects.assert_claim(
            pm, "credit", value, source=ipdb, claim_key=claim_key
        )
        call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "missing person slugs" in captured.out

    def test_missing_role_in_credit_claim(self, db, ipdb, capsys):
        Person.objects.create(name="Pat Lawlor", slug="pat-lawlor")
        pm = MachineModel.objects.create(name="Test", slug="test-model")
        from apps.catalog.claims import build_relationship_claim

        claim_key, value = build_relationship_claim(
            "credit", {"person_slug": "pat-lawlor", "role": "ghost-role"}
        )
        Claim.objects.assert_claim(
            pm, "credit", value, source=ipdb, claim_key=claim_key
        )
        call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "missing role slugs" in captured.out


class TestUncuratedThemes:
    def test_auto_created_themes_noted(self, db, ipdb, pinbase_source, capsys):
        # Curated theme — has a pinbase name claim.
        curated = Theme.objects.create(name="Sports", slug="sports")
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Theme)
        Claim.objects.create(
            content_type=ct,
            object_id=curated.pk,
            source=pinbase_source,
            field_name="name",
            claim_key="name",
            value="Sports",
        )

        # Uncurated theme — no pinbase claim.
        Theme.objects.create(name="Basebal", slug="basebal")

        call_command("validate_catalog")
        captured = capsys.readouterr()
        assert "auto-created" in captured.out
        assert "basebal" in captured.out
