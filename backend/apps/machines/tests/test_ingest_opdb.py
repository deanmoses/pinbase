"""Integration tests for the ingest_opdb command."""

import pytest
from django.core.management import call_command

from apps.machines.models import Claim, PinballModel, Source

FIXTURES = "apps/machines/tests/fixtures"


@pytest.fixture
def _setup_ipdb_first(db):
    """Seed IPDB data so OPDB can match by ipdb_id."""
    call_command("ingest_ipdb", ipdb=f"{FIXTURES}/ipdb_sample.json")


@pytest.fixture
def _run_opdb(db, _setup_ipdb_first):
    """Run ingest_opdb after IPDB seed."""
    call_command("ingest_opdb", opdb=f"{FIXTURES}/opdb_sample.json")


@pytest.mark.django_db
@pytest.mark.usefixtures("_run_opdb")
class TestIngestOpdb:
    def test_creates_source(self):
        source = Source.objects.get(slug="opdb")
        assert source.name == "OPDB"
        assert source.priority == 20

    def test_matches_by_ipdb_id(self):
        # Medieval Madness has ipdb_id=4000 in both dumps.
        pm = PinballModel.objects.get(ipdb_id=4000)
        assert pm.opdb_id == "ABC12-test1"

    def test_skips_aliases(self):
        # The alias record (GHI56-alias) should not create a PinballModel.
        assert not PinballModel.objects.filter(opdb_id="GHI56-alias").exists()

    def test_creates_new_for_unmatched(self):
        # "Stern Exclusive Game" has no ipdb_id, should be a new model.
        pm = PinballModel.objects.get(opdb_id="DEF34-test2")
        assert pm.name == "Stern Exclusive Game"

    def test_opdb_claims_exist(self):
        pm = PinballModel.objects.get(opdb_id="DEF34-test2")
        source = Source.objects.get(slug="opdb")
        claims = Claim.objects.filter(model=pm, source=source, is_active=True)
        field_names = set(claims.values_list("field_name", flat=True))
        assert "name" in field_names
        assert "display_type" in field_names
        assert "machine_type" in field_names
        assert "year" in field_names

    def test_opdb_display_type_claim(self):
        pm = PinballModel.objects.get(opdb_id="ABC12-test1")
        source = Source.objects.get(slug="opdb")
        display_claim = Claim.objects.get(
            model=pm, source=source, field_name="display_type", is_active=True
        )
        assert display_claim.value == "dmd"

    def test_opdb_manufacturer_claim(self):
        pm = PinballModel.objects.get(opdb_id="ABC12-test1")
        source = Source.objects.get(slug="opdb")
        mfr_claim = Claim.objects.get(
            model=pm, source=source, field_name="manufacturer", is_active=True
        )
        assert mfr_claim.value == 7  # Williams OPDB manufacturer_id

    def test_total_model_count(self):
        # 4 from IPDB + 1 new from OPDB = 5 total.
        assert PinballModel.objects.count() == 5

    def test_idempotent(self):
        call_command("ingest_opdb", opdb=f"{FIXTURES}/opdb_sample.json")
        assert PinballModel.objects.count() == 5
