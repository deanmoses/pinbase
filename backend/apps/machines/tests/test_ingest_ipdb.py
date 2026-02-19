"""Integration tests for the ingest_ipdb command."""

import pytest
from django.core.management import call_command

from apps.machines.models import Claim, DesignCredit, Person, PinballModel, Source

FIXTURES = "apps/machines/tests/fixtures"


@pytest.fixture
def _run_ipdb(db):
    """Run ingest_ipdb with the sample fixture."""
    call_command("ingest_ipdb", ipdb=f"{FIXTURES}/ipdb_sample.json")


@pytest.mark.django_db
@pytest.mark.usefixtures("_run_ipdb")
class TestIngestIpdb:
    def test_creates_source(self):
        source = Source.objects.get(slug="ipdb")
        assert source.name == "IPDB"
        assert source.priority == 10

    def test_creates_models(self):
        assert PinballModel.objects.count() == 4
        assert PinballModel.objects.filter(ipdb_id=4000).exists()
        assert PinballModel.objects.filter(ipdb_id=20).exists()
        assert PinballModel.objects.filter(ipdb_id=61).exists()
        assert PinballModel.objects.filter(ipdb_id=100).exists()

    def test_claims_created(self):
        pm = PinballModel.objects.get(ipdb_id=4000)
        source = Source.objects.get(slug="ipdb")
        active_claims = Claim.objects.filter(model=pm, source=source, is_active=True)

        # Should have claims for: name, ipdb_id, manufacturer, player_count,
        # theme, production_quantity, mpu, ipdb_rating, model_number,
        # notable_features, toys, abbreviation, year, month, machine_type,
        # image_urls = 16 claims
        claim_fields = set(active_claims.values_list("field_name", flat=True))
        assert "name" in claim_fields
        assert "year" in claim_fields
        assert "manufacturer" in claim_fields
        assert "machine_type" in claim_fields
        assert "ipdb_rating" in claim_fields

    def test_date_parsing(self):
        pm = PinballModel.objects.get(ipdb_id=4000)
        source = Source.objects.get(slug="ipdb")
        year_claim = Claim.objects.get(
            model=pm, source=source, field_name="year", is_active=True
        )
        assert year_claim.value == 1997
        month_claim = Claim.objects.get(
            model=pm, source=source, field_name="month", is_active=True
        )
        assert month_claim.value == 6

    def test_year_only_date(self):
        # ABC Bowler has DateOfManufacture "1941-01-01T00:00:00" (Jan 1 placeholder).
        pm = PinballModel.objects.get(ipdb_id=20)
        source = Source.objects.get(slug="ipdb")
        year_claim = Claim.objects.get(
            model=pm, source=source, field_name="year", is_active=True
        )
        assert year_claim.value == 1941
        # Month should not be claimed (placeholder).
        assert not Claim.objects.filter(
            model=pm, source=source, field_name="month", is_active=True
        ).exists()

    def test_credits_created(self):
        pm = PinballModel.objects.get(ipdb_id=4000)
        credits = DesignCredit.objects.filter(model=pm)
        # Brian Eddy (design), John Youssi + Greg Freres (art), Lyman Sheats (software)
        assert credits.count() == 4
        assert credits.filter(role="design", person__name="Brian Eddy").exists()
        assert credits.filter(role="art", person__name="John Youssi").exists()
        assert credits.filter(role="software", person__name="Lyman Sheats").exists()

    def test_multi_credit_string(self):
        # Addams Family: "Pat Lawlor, Larry DeMar" for design
        pm = PinballModel.objects.get(ipdb_id=61)
        design_credits = DesignCredit.objects.filter(model=pm, role="design")
        assert design_credits.count() == 2
        names = set(design_credits.values_list("person__name", flat=True))
        assert names == {"Pat Lawlor", "Larry DeMar"}

    def test_persons_created(self):
        # Should have: Brian Eddy, John Youssi, Greg Freres, Lyman Sheats,
        # Pat Lawlor, Larry DeMar = 6 unique people
        assert Person.objects.count() == 6

    def test_pure_mechanical_type(self):
        # Baffle Ball has TypeShortName="" but Type="Pure Mechanical".
        pm = PinballModel.objects.get(ipdb_id=100)
        source = Source.objects.get(slug="ipdb")
        type_claim = Claim.objects.get(
            model=pm, source=source, field_name="machine_type", is_active=True
        )
        assert type_claim.value == "PM"

    def test_idempotent(self):
        # Run again.
        call_command("ingest_ipdb", ipdb=f"{FIXTURES}/ipdb_sample.json")
        # Same 4 models.
        assert PinballModel.objects.count() == 4
        # Same 6 people.
        assert Person.objects.count() == 6
