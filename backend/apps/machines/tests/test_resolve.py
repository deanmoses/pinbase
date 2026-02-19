import pytest

from apps.machines.models import (
    Claim,
    Manufacturer,
    ManufacturerEntity,
    PinballModel,
    Source,
)
from apps.machines.resolve import resolve_model


@pytest.fixture
def ipdb(db):
    return Source.objects.create(name="IPDB", source_type="database", priority=10)


@pytest.fixture
def opdb(db):
    return Source.objects.create(name="OPDB", source_type="database", priority=20)


@pytest.fixture
def editorial(db):
    return Source.objects.create(
        name="The Flip Editorial", source_type="editorial", priority=100
    )


@pytest.fixture
def pm(db):
    return PinballModel.objects.create(name="Placeholder")


class TestResolveModel:
    def test_basic_resolution(self, pm, ipdb):
        Claim.objects.assert_claim(pm, ipdb, "name", "Medieval Madness")
        Claim.objects.assert_claim(pm, ipdb, "year", 1997)
        Claim.objects.assert_claim(pm, ipdb, "machine_type", "SS")

        resolved = resolve_model(pm)
        assert resolved.name == "Medieval Madness"
        assert resolved.year == 1997
        assert resolved.machine_type == "SS"

    def test_higher_priority_wins(self, pm, ipdb, editorial):
        Claim.objects.assert_claim(pm, ipdb, "year", 1996)
        Claim.objects.assert_claim(pm, editorial, "year", 1997)

        resolved = resolve_model(pm)
        assert resolved.year == 1997  # editorial has higher priority

    def test_same_priority_latest_wins(self, pm, ipdb, opdb):
        # opdb has priority 20, ipdb has priority 10 — opdb wins by priority.
        Claim.objects.assert_claim(pm, ipdb, "name", "IPDB Name")
        Claim.objects.assert_claim(pm, opdb, "name", "OPDB Name")

        resolved = resolve_model(pm)
        assert resolved.name == "OPDB Name"

    def test_extra_data_catchall(self, pm, ipdb):
        Claim.objects.assert_claim(pm, ipdb, "model_number", "20021")
        Claim.objects.assert_claim(pm, ipdb, "abbreviation", "MM")

        resolved = resolve_model(pm)
        assert resolved.extra_data["model_number"] == "20021"
        assert resolved.extra_data["abbreviation"] == "MM"

    def test_manufacturer_resolution_by_ipdb_id(self, pm, ipdb):
        mfr = Manufacturer.objects.create(name="Williams")
        ManufacturerEntity.objects.create(
            manufacturer=mfr, name="Williams Manufacturing", ipdb_manufacturer_id=42
        )
        Claim.objects.assert_claim(pm, ipdb, "manufacturer", 42)

        resolved = resolve_model(pm)
        assert resolved.manufacturer == mfr

    def test_manufacturer_resolution_by_opdb_id(self, pm, opdb):
        mfr = Manufacturer.objects.create(name="Williams", opdb_manufacturer_id=7)
        Claim.objects.assert_claim(pm, opdb, "manufacturer", 7)

        resolved = resolve_model(pm)
        assert resolved.manufacturer == mfr

    def test_manufacturer_resolution_by_name(self, pm, ipdb):
        mfr = Manufacturer.objects.create(name="Stern")
        Claim.objects.assert_claim(pm, ipdb, "manufacturer", "Stern")

        resolved = resolve_model(pm)
        assert resolved.manufacturer == mfr

    def test_manufacturer_resolution_by_trade_name(self, pm, ipdb):
        mfr = Manufacturer.objects.create(
            name="Midway Manufacturing", trade_name="Bally"
        )
        Claim.objects.assert_claim(pm, ipdb, "manufacturer", "Bally")

        resolved = resolve_model(pm)
        assert resolved.manufacturer == mfr

    def test_manufacturer_resolution_disambiguates_opdb_from_ipdb(self, pm, ipdb, opdb):
        """OPDB manufacturer_id that collides with an IPDB entity ID resolves correctly."""
        colliding_id = 7
        # IPDB entity with the same numeric ID
        ipdb_mfr = Manufacturer.objects.create(name="Some IPDB Brand")
        ManufacturerEntity.objects.create(
            manufacturer=ipdb_mfr,
            name="Some IPDB Corp",
            ipdb_manufacturer_id=colliding_id,
        )
        # OPDB manufacturer with the same numeric ID
        opdb_mfr = Manufacturer.objects.create(
            name="Stern", opdb_manufacturer_id=colliding_id
        )
        # OPDB claim should resolve to the OPDB manufacturer, not the IPDB entity.
        Claim.objects.assert_claim(pm, opdb, "manufacturer", colliding_id)
        resolved = resolve_model(pm)
        assert resolved.manufacturer == opdb_mfr

    def test_manufacturer_resolution_unknown(self, pm, ipdb):
        Claim.objects.assert_claim(pm, ipdb, "manufacturer", "NonexistentCorp")
        resolved = resolve_model(pm)
        assert resolved.manufacturer is None

    def test_int_coercion(self, pm, ipdb):
        Claim.objects.assert_claim(pm, ipdb, "year", "1997")
        Claim.objects.assert_claim(pm, ipdb, "player_count", "4")

        resolved = resolve_model(pm)
        assert resolved.year == 1997
        assert resolved.player_count == 4

    def test_decimal_coercion(self, pm, ipdb):
        from decimal import Decimal

        Claim.objects.assert_claim(pm, ipdb, "ipdb_rating", "8.75")

        resolved = resolve_model(pm)
        assert resolved.ipdb_rating == Decimal("8.75")

    def test_empty_string_coercion(self, pm, ipdb):
        Claim.objects.assert_claim(pm, ipdb, "year", "")
        resolved = resolve_model(pm)
        assert resolved.year is None

    def test_invalid_int_coercion(self, pm, ipdb):
        Claim.objects.assert_claim(pm, ipdb, "year", "not-a-number")
        resolved = resolve_model(pm)
        assert resolved.year is None

    def test_stale_values_cleared_on_re_resolve(self, pm, ipdb):
        """Deactivated claims should not leave ghost values after re-resolution."""
        Claim.objects.assert_claim(pm, ipdb, "year", 1997)
        Claim.objects.assert_claim(pm, ipdb, "theme", "Medieval")
        Claim.objects.assert_claim(pm, ipdb, "abbreviation", "MM")
        resolve_model(pm)
        assert pm.year == 1997
        assert pm.theme == "Medieval"
        assert pm.extra_data["abbreviation"] == "MM"

        # Deactivate all claims — simulates source retraction.
        Claim.objects.filter(model=pm, is_active=True).update(is_active=False)
        resolve_model(pm)
        pm.refresh_from_db()
        assert pm.year is None
        assert pm.theme == ""
        assert pm.extra_data == {}

    def test_mixed_fields_and_extra_data(self, pm, ipdb, editorial):
        Claim.objects.assert_claim(pm, ipdb, "name", "The Addams Family")
        Claim.objects.assert_claim(pm, ipdb, "year", 1992)
        Claim.objects.assert_claim(pm, ipdb, "toys", "Thing hand, bookcase")
        Claim.objects.assert_claim(pm, editorial, "educational_text", "A seminal game.")

        resolved = resolve_model(pm)
        assert resolved.name == "The Addams Family"
        assert resolved.year == 1992
        assert resolved.extra_data["toys"] == "Thing hand, bookcase"
        assert resolved.educational_text == "A seminal game."
