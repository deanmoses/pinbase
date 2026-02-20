import pytest
from django.utils import timezone

from apps.machines.models import (
    Claim,
    MachineGroup,
    Manufacturer,
    ManufacturerEntity,
    PinballModel,
    Source,
)
from apps.machines.resolve import resolve_all, resolve_model


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


@pytest.mark.django_db
class TestResolveAll:
    def test_basic(self):
        ipdb = Source.objects.create(
            name="IPDB", slug="ipdb", source_type="database", priority=10
        )
        pm1 = PinballModel.objects.create(name="P1", slug="p1")
        pm2 = PinballModel.objects.create(name="P2", slug="p2")
        pm3 = PinballModel.objects.create(name="P3", slug="p3")

        Claim.objects.assert_claim(pm1, ipdb, "name", "Medieval Madness")
        Claim.objects.assert_claim(pm1, ipdb, "year", 1997)
        Claim.objects.assert_claim(pm2, ipdb, "name", "The Addams Family")
        Claim.objects.assert_claim(pm3, ipdb, "name", "Twilight Zone")
        Claim.objects.assert_claim(pm3, ipdb, "machine_type", "SS")

        before = timezone.now()
        count = resolve_all()
        assert count == 3

        pm1.refresh_from_db()
        pm2.refresh_from_db()
        pm3.refresh_from_db()
        assert pm1.name == "Medieval Madness"
        assert pm1.year == 1997
        assert pm2.name == "The Addams Family"
        assert pm3.name == "Twilight Zone"
        assert pm3.machine_type == "SS"

        # updated_at should be refreshed.
        assert pm1.updated_at >= before
        assert pm2.updated_at >= before
        assert pm3.updated_at >= before

    def test_matches_resolve_model(self):
        """Bulk resolve produces identical results to per-model resolve."""
        ipdb = Source.objects.create(
            name="IPDB", slug="ipdb", source_type="database", priority=10
        )
        opdb = Source.objects.create(
            name="OPDB", slug="opdb", source_type="database", priority=20
        )
        mfr = Manufacturer.objects.create(name="Williams", opdb_manufacturer_id=7)
        ManufacturerEntity.objects.create(
            manufacturer=mfr, name="Williams Corp", ipdb_manufacturer_id=42
        )
        MachineGroup.objects.create(opdb_id="G1111", name="Medieval Madness", slug="mm")

        pm_bulk = PinballModel.objects.create(name="P1", slug="p1")
        pm_single = PinballModel.objects.create(name="P2", slug="p2")

        # Same claims on both models.
        for pm in (pm_bulk, pm_single):
            Claim.objects.assert_claim(pm, ipdb, "name", "Medieval Madness")
            Claim.objects.assert_claim(pm, opdb, "year", 1997)
            Claim.objects.assert_claim(pm, ipdb, "manufacturer", 42)
            Claim.objects.assert_claim(pm, opdb, "group", "G1111")
            Claim.objects.assert_claim(pm, ipdb, "abbreviation", "MM")
            Claim.objects.assert_claim(pm, ipdb, "machine_type", "SS")

        # Resolve pm_single with the per-model path.
        resolve_model(pm_single)
        pm_single.refresh_from_db()

        # Resolve pm_bulk with the bulk path.
        resolve_all()
        pm_bulk.refresh_from_db()

        assert pm_bulk.name == pm_single.name
        assert pm_bulk.year == pm_single.year
        assert pm_bulk.manufacturer_id == pm_single.manufacturer_id
        assert pm_bulk.group_id == pm_single.group_id
        assert pm_bulk.machine_type == pm_single.machine_type
        assert pm_bulk.extra_data == pm_single.extra_data

    def test_opdb_conflict(self):
        """Two models resolving to same opdb_id — first by name order wins."""
        ipdb = Source.objects.create(
            name="IPDB", slug="ipdb", source_type="database", priority=10
        )
        # "Alpha" sorts before "Beta" — Alpha should keep the opdb_id.
        pm_a = PinballModel.objects.create(name="Alpha", slug="alpha")
        pm_b = PinballModel.objects.create(name="Beta", slug="beta")

        Claim.objects.assert_claim(pm_a, ipdb, "opdb_id", "GCONFLICT-M1")
        Claim.objects.assert_claim(pm_b, ipdb, "opdb_id", "GCONFLICT-M1")

        resolve_all()
        pm_a.refresh_from_db()
        pm_b.refresh_from_db()

        assert pm_a.opdb_id == "GCONFLICT-M1"
        assert pm_b.opdb_id is None

    def test_stale_values_cleared(self):
        ipdb = Source.objects.create(
            name="IPDB", slug="ipdb", source_type="database", priority=10
        )
        pm = PinballModel.objects.create(name="P1", slug="p1")

        Claim.objects.assert_claim(pm, ipdb, "year", 1997)
        Claim.objects.assert_claim(pm, ipdb, "theme", "Medieval")
        Claim.objects.assert_claim(pm, ipdb, "abbreviation", "MM")
        resolve_all()
        pm.refresh_from_db()
        assert pm.year == 1997
        assert pm.theme == "Medieval"
        assert pm.extra_data["abbreviation"] == "MM"

        # Deactivate all claims.
        Claim.objects.filter(model=pm, is_active=True).update(is_active=False)
        resolve_all()
        pm.refresh_from_db()
        assert pm.year is None
        assert pm.theme == ""
        assert pm.extra_data == {}

    def test_query_count(self, django_assert_max_num_queries):
        ipdb = Source.objects.create(
            name="IPDB", slug="ipdb", source_type="database", priority=10
        )
        for i in range(5):
            pm = PinballModel.objects.create(name=f"Model {i}", slug=f"model-{i}")
            Claim.objects.assert_claim(pm, ipdb, "name", f"Resolved {i}")
            Claim.objects.assert_claim(pm, ipdb, "year", 2000 + i)

        # Should be ~6 queries: 2 manufacturer lookups + 1 groups + 1 claims
        # + 1 models + 1 bulk_update.
        with django_assert_max_num_queries(10):
            resolve_all()
