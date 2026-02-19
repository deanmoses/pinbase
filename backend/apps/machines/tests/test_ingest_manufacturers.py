"""Integration tests for the ingest_manufacturers command."""

import pytest
from django.core.management import call_command

from apps.machines.models import Manufacturer, ManufacturerEntity

FIXTURES = "apps/machines/tests/fixtures"


@pytest.mark.django_db
class TestIngestManufacturers:
    def test_creates_brands_and_entities(self):
        call_command(
            "ingest_manufacturers",
            ipdb=f"{FIXTURES}/ipdb_sample.json",
            opdb=f"{FIXTURES}/opdb_sample.json",
        )
        # IPDB sample has 3 ManufacturerIds: 351 (Williams), 93 (Gottlieb), 349 (Bally).
        assert ManufacturerEntity.objects.count() == 3
        # Trade names: Williams, Gottlieb, Bally → 3 brands.
        assert Manufacturer.objects.count() >= 3

        # Verify Williams entity.
        williams_entity = ManufacturerEntity.objects.get(ipdb_manufacturer_id=351)
        assert williams_entity.manufacturer.name == "Williams"

        # Verify Gottlieb entity.
        gottlieb_entity = ManufacturerEntity.objects.get(ipdb_manufacturer_id=93)
        assert gottlieb_entity.manufacturer.name == "Gottlieb"

    def test_opdb_matches_existing_brands(self):
        call_command(
            "ingest_manufacturers",
            ipdb=f"{FIXTURES}/ipdb_sample.json",
            opdb=f"{FIXTURES}/opdb_sample.json",
        )
        # OPDB sample has Williams (id=7) and Stern (id=12).
        # Williams should match the IPDB-created brand.
        williams = Manufacturer.objects.get(name="Williams")
        assert williams.opdb_manufacturer_id == 7

        # Stern has no IPDB match, so it should be created.
        stern = Manufacturer.objects.get(name="Stern")
        assert stern.opdb_manufacturer_id == 12

    def test_idempotent(self):
        call_command(
            "ingest_manufacturers",
            ipdb=f"{FIXTURES}/ipdb_sample.json",
            opdb=f"{FIXTURES}/opdb_sample.json",
        )
        count1 = Manufacturer.objects.count()
        entity_count1 = ManufacturerEntity.objects.count()

        # Run again — should be idempotent.
        call_command(
            "ingest_manufacturers",
            ipdb=f"{FIXTURES}/ipdb_sample.json",
            opdb=f"{FIXTURES}/opdb_sample.json",
        )
        assert Manufacturer.objects.count() == count1
        assert ManufacturerEntity.objects.count() == entity_count1
