import pytest
from django.test import Client

from apps.machines.models import (
    Claim,
    DesignCredit,
    MachineGroup,
    Manufacturer,
    ManufacturerEntity,
    Person,
    PinballModel,
    Source,
)

SAMPLE_IMAGES = [
    {
        "primary": True,
        "type": "backglass",
        "urls": {
            "small": "https://img.opdb.org/sm.jpg",
            "medium": "https://img.opdb.org/md.jpg",
            "large": "https://img.opdb.org/lg.jpg",
        },
    }
]


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def source(db):
    return Source.objects.create(name="IPDB", source_type="database", priority=10)


@pytest.fixture
def manufacturer(db):
    return Manufacturer.objects.create(name="Williams", trade_name="Williams")


@pytest.fixture
def stern(db):
    return Manufacturer.objects.create(name="Stern", trade_name="Stern")


@pytest.fixture
def person(db):
    return Person.objects.create(name="Pat Lawlor")


@pytest.fixture
def pinball_model(db, manufacturer):
    return PinballModel.objects.create(
        name="Medieval Madness",
        manufacturer=manufacturer,
        year=1997,
        machine_type="SS",
        display_type="dmd",
        theme="Medieval",
    )


@pytest.fixture
def another_model(db, stern):
    return PinballModel.objects.create(
        name="The Mandalorian",
        manufacturer=stern,
        year=2021,
        machine_type="SS",
        display_type="lcd",
        theme="Star Wars",
    )


class TestModelsAPI:
    def test_list_models(self, client, pinball_model):
        resp = client.get("/api/models/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Medieval Madness"

    def test_list_models_filter_manufacturer(
        self, client, pinball_model, another_model
    ):
        resp = client.get("/api/models/?manufacturer=williams")
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Medieval Madness"

    def test_list_models_filter_type(self, client, pinball_model):
        resp = client.get("/api/models/?type=SS")
        data = resp.json()
        assert data["count"] == 1

        resp = client.get("/api/models/?type=EM")
        data = resp.json()
        assert data["count"] == 0

    def test_list_models_filter_year_range(self, client, pinball_model, another_model):
        resp = client.get("/api/models/?year_min=2000&year_max=2025")
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "The Mandalorian"

    def test_list_models_search(self, client, pinball_model, another_model):
        resp = client.get("/api/models/?search=Medieval")
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Medieval Madness"

    def test_list_models_search_manufacturer(self, client, pinball_model):
        resp = client.get("/api/models/?search=Williams")
        data = resp.json()
        assert data["count"] == 1

    def test_list_models_filter_person(self, client, pinball_model, person):
        DesignCredit.objects.create(model=pinball_model, person=person, role="design")
        resp = client.get("/api/models/?person=pat-lawlor")
        data = resp.json()
        assert data["count"] == 1

    def test_list_models_ordering(self, client, pinball_model, another_model):
        resp = client.get("/api/models/?ordering=-year")
        data = resp.json()
        assert data["items"][0]["name"] == "The Mandalorian"

    def test_list_models_excludes_aliases(self, client, pinball_model):
        PinballModel.objects.create(
            name="Medieval Madness (LE)",
            machine_type="SS",
            display_type="dmd",
            alias_of=pinball_model,
        )
        resp = client.get("/api/models/")
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Medieval Madness"

    def test_list_models_thumbnail(self, client, manufacturer, db):
        PinballModel.objects.create(
            name="With Image",
            manufacturer=manufacturer,
            machine_type="SS",
            display_type="dmd",
            extra_data={"images": SAMPLE_IMAGES},
        )
        resp = client.get("/api/models/")
        data = resp.json()
        assert data["items"][0]["thumbnail_url"] == "https://img.opdb.org/md.jpg"

    def test_get_model_detail(self, client, pinball_model, person, source):
        DesignCredit.objects.create(model=pinball_model, person=person, role="design")
        Claim.objects.assert_claim(
            pinball_model, source, "year", 1997, citation="IPDB entry"
        )

        resp = client.get(f"/api/models/{pinball_model.slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Medieval Madness"
        assert len(data["credits"]) == 1
        assert data["credits"][0]["person_name"] == "Pat Lawlor"
        year_claims = [c for c in data["activity"] if c["field_name"] == "year"]
        assert len(year_claims) == 1
        assert year_claims[0]["source_name"] == "IPDB"
        assert year_claims[0]["is_winner"] is True

    def test_get_model_detail_images(self, client, manufacturer, db):
        pm = PinballModel.objects.create(
            name="With Image",
            manufacturer=manufacturer,
            machine_type="SS",
            display_type="dmd",
            extra_data={"images": SAMPLE_IMAGES},
        )
        resp = client.get(f"/api/models/{pm.slug}")
        data = resp.json()
        assert data["thumbnail_url"] == "https://img.opdb.org/md.jpg"
        assert data["hero_image_url"] == "https://img.opdb.org/lg.jpg"

    def test_get_model_detail_no_images(self, client, pinball_model):
        resp = client.get(f"/api/models/{pinball_model.slug}")
        data = resp.json()
        assert data["thumbnail_url"] is None
        assert data["hero_image_url"] is None

    def test_get_model_detail_features(self, client, manufacturer, db):
        pm = PinballModel.objects.create(
            name="With Features",
            manufacturer=manufacturer,
            machine_type="SS",
            display_type="dmd",
            extra_data={"features": ["Castle attack", "Gold trim"]},
        )
        resp = client.get(f"/api/models/{pm.slug}")
        data = resp.json()
        assert data["features"] == ["Castle attack", "Gold trim"]

    def test_get_model_detail_aliases(self, client, pinball_model):
        PinballModel.objects.create(
            name="Medieval Madness (LE)",
            machine_type="SS",
            display_type="dmd",
            alias_of=pinball_model,
            extra_data={"features": ["Gold trim"]},
        )
        resp = client.get(f"/api/models/{pinball_model.slug}")
        data = resp.json()
        assert len(data["aliases"]) == 1
        assert data["aliases"][0]["name"] == "Medieval Madness (LE)"
        assert data["aliases"][0]["features"] == ["Gold trim"]

    def test_get_model_detail_group(self, client, pinball_model, db):
        group = MachineGroup.objects.create(
            name="Medieval Madness", opdb_id="G5pe4", shortname="MM"
        )
        pinball_model.group = group
        pinball_model.save()
        resp = client.get(f"/api/models/{pinball_model.slug}")
        data = resp.json()
        assert data["group_name"] == "Medieval Madness"
        assert data["group_slug"] == group.slug

    def test_get_model_detail_no_group(self, client, pinball_model):
        resp = client.get(f"/api/models/{pinball_model.slug}")
        data = resp.json()
        assert data["group_name"] is None
        assert data["group_slug"] is None

    def test_get_model_404(self, client, db):
        resp = client.get("/api/models/nonexistent")
        assert resp.status_code == 404


class TestGroupsAPI:
    @pytest.fixture
    def group(self, db):
        return MachineGroup.objects.create(
            name="Medieval Madness", opdb_id="G5pe4", shortname="MM"
        )

    @pytest.fixture
    def group_with_machines(self, group, manufacturer):
        PinballModel.objects.create(
            name="Medieval Madness",
            manufacturer=manufacturer,
            year=1997,
            machine_type="SS",
            display_type="dmd",
            group=group,
            extra_data={"images": SAMPLE_IMAGES},
        )
        PinballModel.objects.create(
            name="Medieval Madness (Remake)",
            manufacturer=manufacturer,
            year=2015,
            machine_type="SS",
            display_type="dmd",
            group=group,
        )
        return group

    def test_list_groups(self, client, group_with_machines):
        resp = client.get("/api/groups/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        item = data["items"][0]
        assert item["name"] == "Medieval Madness"
        assert item["shortname"] == "MM"
        assert item["machine_count"] == 2

    def test_list_groups_search(self, client, group_with_machines, db):
        MachineGroup.objects.create(
            name="Attack From Mars", opdb_id="G1234", shortname="AFM"
        )
        resp = client.get("/api/groups/?search=MM")
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["shortname"] == "MM"

    def test_list_groups_thumbnail(self, client, group_with_machines):
        resp = client.get("/api/groups/")
        data = resp.json()
        assert data["items"][0]["thumbnail_url"] == "https://img.opdb.org/md.jpg"

    def test_list_groups_empty_group(self, client, group):
        resp = client.get("/api/groups/")
        data = resp.json()
        assert data["items"][0]["machine_count"] == 0
        assert data["items"][0]["thumbnail_url"] is None

    def test_get_group_detail(self, client, group_with_machines):
        resp = client.get(f"/api/groups/{group_with_machines.slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Medieval Madness"
        assert len(data["machines"]) == 2

    def test_get_group_detail_excludes_aliases(self, client, group_with_machines):
        parent = PinballModel.objects.get(name="Medieval Madness")
        PinballModel.objects.create(
            name="Medieval Madness (LE)",
            machine_type="SS",
            display_type="dmd",
            group=group_with_machines,
            alias_of=parent,
        )
        resp = client.get(f"/api/groups/{group_with_machines.slug}")
        data = resp.json()
        # Only non-alias machines should appear.
        assert len(data["machines"]) == 2
        names = [m["name"] for m in data["machines"]]
        assert "Medieval Madness (LE)" not in names

    def test_machine_count_excludes_aliases(self, client, group_with_machines):
        parent = PinballModel.objects.get(name="Medieval Madness")
        PinballModel.objects.create(
            name="Medieval Madness (LE)",
            machine_type="SS",
            display_type="dmd",
            group=group_with_machines,
            alias_of=parent,
        )
        resp = client.get("/api/groups/")
        data = resp.json()
        assert data["items"][0]["machine_count"] == 2

    def test_get_group_404(self, client, db):
        resp = client.get("/api/groups/nonexistent")
        assert resp.status_code == 404


class TestManufacturersAPI:
    def test_list_manufacturers(self, client, manufacturer, pinball_model):
        resp = client.get("/api/manufacturers/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Williams"
        assert data["items"][0]["model_count"] == 1

    def test_get_manufacturer_detail(self, client, manufacturer, pinball_model):
        ManufacturerEntity.objects.create(
            manufacturer=manufacturer,
            name="Williams Manufacturing Company",
            ipdb_manufacturer_id=350,
            years_active="1943-1985",
        )
        resp = client.get(f"/api/manufacturers/{manufacturer.slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Williams"
        assert len(data["entities"]) == 1
        assert data["entities"][0]["name"] == "Williams Manufacturing Company"
        assert data["entities"][0]["ipdb_manufacturer_id"] == 350
        assert len(data["models"]) == 1
        assert data["models"][0]["name"] == "Medieval Madness"


class TestPeopleAPI:
    def test_list_people(self, client, person, pinball_model):
        DesignCredit.objects.create(model=pinball_model, person=person, role="design")
        resp = client.get("/api/people/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Pat Lawlor"
        assert data["items"][0]["credit_count"] == 1

    def test_get_person_detail(self, client, person, pinball_model):
        DesignCredit.objects.create(model=pinball_model, person=person, role="design")
        resp = client.get(f"/api/people/{person.slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Pat Lawlor"
        assert len(data["machines"]) == 1
        assert data["machines"][0]["model_name"] == "Medieval Madness"
        assert data["machines"][0]["roles"] == ["Design"]


class TestSourcesAPI:
    def test_list_sources(self, client, source):
        resp = client.get("/api/sources/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "IPDB"
