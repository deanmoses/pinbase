"""Integration tests for the ingest_opdb command."""

import json
import tempfile

import pytest
from django.core.management import call_command

from apps.machines.models import Claim, MachineGroup, MachineModel, Source

FIXTURES = "apps/machines/tests/fixtures"


@pytest.fixture
def _setup_ipdb_first(db):
    """Seed IPDB data so OPDB can match by ipdb_id."""
    call_command("ingest_ipdb", ipdb=f"{FIXTURES}/ipdb_sample.json")


@pytest.fixture
def _run_opdb(db, _setup_ipdb_first):
    """Run ingest_opdb with groups after IPDB seed."""
    call_command(
        "ingest_opdb",
        opdb=f"{FIXTURES}/opdb_sample.json",
        groups=f"{FIXTURES}/opdb_groups_sample.json",
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("_run_opdb")
class TestIngestOpdb:
    def test_creates_source(self):
        source = Source.objects.get(slug="opdb")
        assert source.name == "OPDB"
        assert source.priority == 200

    def test_matches_by_ipdb_id(self):
        # Medieval Madness has ipdb_id=4000 in both dumps.
        pm = MachineModel.objects.get(ipdb_id=4000)
        assert pm.opdb_id == "G1111-MTest1"

    def test_creates_new_for_unmatched(self):
        # "Stern Exclusive Game" has no ipdb_id, should be a new model.
        pm = MachineModel.objects.get(opdb_id="G2222-MTest2")
        assert pm.name == "Stern Exclusive Game"

    def test_opdb_claims_exist(self):
        pm = MachineModel.objects.get(opdb_id="G2222-MTest2")
        source = Source.objects.get(slug="opdb")
        claims = Claim.objects.filter(model=pm, source=source, is_active=True)
        field_names = set(claims.values_list("field_name", flat=True))
        assert "name" in field_names
        assert "display_type" in field_names
        assert "machine_type" in field_names
        assert "year" in field_names

    def test_opdb_display_type_claim(self):
        pm = MachineModel.objects.get(opdb_id="G1111-MTest1")
        source = Source.objects.get(slug="opdb")
        display_claim = Claim.objects.get(
            model=pm, source=source, field_name="display_type", is_active=True
        )
        assert display_claim.value == "dmd"

    def test_opdb_manufacturer_claim(self):
        pm = MachineModel.objects.get(opdb_id="G1111-MTest1")
        source = Source.objects.get(slug="opdb")
        mfr_claim = Claim.objects.get(
            model=pm, source=source, field_name="manufacturer", is_active=True
        )
        assert mfr_claim.value == 7  # Williams OPDB manufacturer_id

    def test_idempotent(self):
        initial_count = MachineModel.objects.count()
        call_command(
            "ingest_opdb",
            opdb=f"{FIXTURES}/opdb_sample.json",
            groups=f"{FIXTURES}/opdb_groups_sample.json",
        )
        assert MachineModel.objects.count() == initial_count


@pytest.mark.django_db
@pytest.mark.usefixtures("_run_opdb")
class TestIngestOpdbNewFields:
    """Tests for new field claims: common_name, shortname, images."""

    def test_claims_common_name(self):
        pm = MachineModel.objects.get(opdb_id="G2222-MTest2")
        source = Source.objects.get(slug="opdb")
        claim = Claim.objects.get(
            model=pm, source=source, field_name="common_name", is_active=True
        )
        assert claim.value == "SEG"

    def test_no_common_name_when_null(self):
        pm = MachineModel.objects.get(opdb_id="G1111-MTest1")
        source = Source.objects.get(slug="opdb")
        assert not Claim.objects.filter(
            model=pm, source=source, field_name="common_name", is_active=True
        ).exists()

    def test_claims_shortname(self):
        pm = MachineModel.objects.get(opdb_id="G2222-MTest2")
        source = Source.objects.get(slug="opdb")
        claim = Claim.objects.get(
            model=pm, source=source, field_name="shortname", is_active=True
        )
        assert claim.value == "SEG"

    def test_claims_images(self):
        pm = MachineModel.objects.get(opdb_id="G1111-MTest1")
        source = Source.objects.get(slug="opdb")
        claim = Claim.objects.get(
            model=pm, source=source, field_name="images", is_active=True
        )
        assert len(claim.value) == 1
        assert claim.value[0]["type"] == "backglass"
        assert "large" in claim.value[0]["urls"]

    def test_no_images_when_empty(self):
        pm = MachineModel.objects.get(opdb_id="G2222-MTest2")
        source = Source.objects.get(slug="opdb")
        assert not Claim.objects.filter(
            model=pm, source=source, field_name="images", is_active=True
        ).exists()


@pytest.mark.django_db
@pytest.mark.usefixtures("_run_opdb")
class TestIngestOpdbGroups:
    """Tests for MachineGroup creation and group claims."""

    def test_creates_machine_groups(self):
        assert MachineGroup.objects.count() == 2
        mm = MachineGroup.objects.get(opdb_id="G1111")
        assert mm.name == "Medieval Madness"
        assert mm.short_name == "MM"

    def test_group_claim_on_machine(self):
        pm = MachineModel.objects.get(opdb_id="G1111-MTest1")
        source = Source.objects.get(slug="opdb")
        claim = Claim.objects.get(
            model=pm, source=source, field_name="group", is_active=True
        )
        assert claim.value == "G1111"

    def test_group_claim_on_unmatched_machine(self):
        pm = MachineModel.objects.get(opdb_id="G2222-MTest2")
        source = Source.objects.get(slug="opdb")
        claim = Claim.objects.get(
            model=pm, source=source, field_name="group", is_active=True
        )
        assert claim.value == "G2222"


@pytest.mark.django_db
@pytest.mark.usefixtures("_run_opdb")
class TestIngestOpdbAliases:
    """Tests for alias ingestion with alias_of FK."""

    def test_alias_created(self):
        alias = MachineModel.objects.get(opdb_id="G1111-MTest1-AAlias")
        assert alias.name == "Medieval Madness (LE)"

    def test_alias_linked_to_parent(self):
        parent = MachineModel.objects.get(opdb_id="G1111-MTest1")
        alias = MachineModel.objects.get(opdb_id="G1111-MTest1-AAlias")
        assert alias.alias_of == parent

    def test_alias_has_claims(self):
        alias = MachineModel.objects.get(opdb_id="G1111-MTest1-AAlias")
        source = Source.objects.get(slug="opdb")
        claims = Claim.objects.filter(model=alias, source=source, is_active=True)
        field_names = set(claims.values_list("field_name", flat=True))
        assert "name" in field_names
        assert "features" in field_names
        assert "group" in field_names

    def test_alias_features_claim(self):
        alias = MachineModel.objects.get(opdb_id="G1111-MTest1-AAlias")
        source = Source.objects.get(slug="opdb")
        claim = Claim.objects.get(
            model=alias, source=source, field_name="features", is_active=True
        )
        assert "Gold trim" in claim.value

    def test_total_model_count(self):
        # 4 from IPDB + 1 new machine from OPDB + 1 alias = 6 total.
        assert MachineModel.objects.count() == 6


@pytest.mark.django_db
class TestIngestOpdbChangelog:
    """Tests for changelog pre-processing."""

    def test_changelog_moves_opdb_id(self, db):
        # Create a model with the stale ID.
        MachineModel.objects.create(name="Stale Machine", opdb_id="GSTALE-MOld1")

        call_command(
            "ingest_opdb",
            opdb=f"{FIXTURES}/opdb_sample.json",
            changelog=f"{FIXTURES}/opdb_changelog_sample.json",
        )

        # The stale ID should have been moved.
        pm = MachineModel.objects.get(name="Stale Machine")
        assert pm.opdb_id == "GFRESH-MNew1"

    def test_changelog_does_not_delete(self, db):
        # Create a model with the deleted ID.
        MachineModel.objects.create(name="Dead Machine", opdb_id="GDEAD-MDel1")

        call_command(
            "ingest_opdb",
            opdb=f"{FIXTURES}/opdb_sample.json",
            changelog=f"{FIXTURES}/opdb_changelog_sample.json",
        )

        # The model should still exist (we never delete data).
        assert MachineModel.objects.filter(name="Dead Machine").exists()

    def test_changelog_no_overwrite_existing(self, db):
        # Both the stale and replacement IDs exist.
        MachineModel.objects.create(name="Stale Machine", opdb_id="GSTALE-MOld1")
        MachineModel.objects.create(name="New Machine", opdb_id="GFRESH-MNew1")

        call_command(
            "ingest_opdb",
            opdb=f"{FIXTURES}/opdb_sample.json",
            changelog=f"{FIXTURES}/opdb_changelog_sample.json",
        )

        # The stale one should NOT be overwritten (replacement already taken).
        stale = MachineModel.objects.get(name="Stale Machine")
        assert stale.opdb_id == "GSTALE-MOld1"


def _opdb_dump(machines=None, aliases=None):
    """Write a temporary OPDB JSON dump and return the path."""
    data = []
    for m in machines or []:
        m.setdefault("is_machine", True)
        data.append(m)
    for a in aliases or []:
        a.setdefault("is_alias", True)
        data.append(a)
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name


@pytest.mark.django_db
class TestOpdbSkipsMissingOpdbId:
    """Records without opdb_id are skipped (unmatchable on rerun)."""

    def test_machine_without_opdb_id_skipped(self):
        path = _opdb_dump(machines=[{"name": "No ID Game"}])
        call_command("ingest_opdb", opdb=path)
        assert not MachineModel.objects.filter(name="No ID Game").exists()

    def test_alias_without_opdb_id_skipped(self):
        path = _opdb_dump(aliases=[{"name": "No ID Alias"}])
        call_command("ingest_opdb", opdb=path)
        assert not MachineModel.objects.filter(name="No ID Alias").exists()


@pytest.mark.django_db
class TestOpdbConflictBranches:
    """In-memory opdb_id conflict handling."""

    def test_matched_model_keeps_existing_opdb_id(self):
        """Model matched by ipdb_id already has a different opdb_id → not overwritten."""
        MachineModel.objects.create(name="Test Game", ipdb_id=9999, opdb_id="GOLD-M1")
        path = _opdb_dump(
            machines=[
                {
                    "opdb_id": "GNEW-M1",
                    "ipdb_id": 9999,
                    "name": "Test Game",
                }
            ]
        )
        call_command("ingest_opdb", opdb=path)

        pm = MachineModel.objects.get(ipdb_id=9999)
        assert pm.opdb_id == "GOLD-M1"

    def test_opdb_id_set_when_no_conflict(self):
        """Model matched by ipdb_id has no opdb_id → gets it set."""
        MachineModel.objects.create(name="Test Game", ipdb_id=9999)
        path = _opdb_dump(
            machines=[
                {
                    "opdb_id": "GNEW-M1",
                    "ipdb_id": 9999,
                    "name": "Test Game",
                }
            ]
        )
        call_command("ingest_opdb", opdb=path)

        pm = MachineModel.objects.get(ipdb_id=9999)
        assert pm.opdb_id == "GNEW-M1"

    def test_opdb_id_not_set_when_already_owned(self):
        """Model matched by ipdb_id has no opdb_id, but opdb_id is already taken."""
        MachineModel.objects.create(name="Owner", opdb_id="GNEW-M1")
        MachineModel.objects.create(name="Test Game", ipdb_id=9999)
        path = _opdb_dump(
            machines=[
                {
                    "opdb_id": "GNEW-M1",
                    "ipdb_id": 9999,
                    "name": "Test Game",
                }
            ]
        )
        call_command("ingest_opdb", opdb=path)

        pm = MachineModel.objects.get(ipdb_id=9999)
        assert pm.opdb_id is None


@pytest.mark.django_db
class TestOpdbAliasEdgeCases:
    """Alias-specific edge cases in in-memory matching."""

    def test_alias_skipped_when_parent_missing(self):
        """Alias whose parent opdb_id doesn't exist is skipped."""
        path = _opdb_dump(
            aliases=[
                {
                    "opdb_id": "GORPHAN-M1-AAlias",
                    "name": "Orphan Alias",
                }
            ]
        )
        call_command("ingest_opdb", opdb=path)
        assert not MachineModel.objects.filter(name="Orphan Alias").exists()

    def test_alias_links_to_parent_from_same_run(self):
        """Alias can find a parent that was created in the same ingest run."""
        path = _opdb_dump(
            machines=[
                {
                    "opdb_id": "GNEW-M1",
                    "name": "New Parent",
                }
            ],
            aliases=[
                {
                    "opdb_id": "GNEW-M1-AAlias",
                    "name": "New Alias",
                }
            ],
        )
        call_command("ingest_opdb", opdb=path)

        parent = MachineModel.objects.get(opdb_id="GNEW-M1")
        alias = MachineModel.objects.get(opdb_id="GNEW-M1-AAlias")
        assert alias.alias_of == parent
