import pytest
from django.test import Client

from apps.machines.models import (
    Claim,
    DesignCredit,
    Manufacturer,
    ManufacturerEntity,
    Person,
    PinballModel,
    Source,
)


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
        assert "year" in data["provenance"]
        assert data["provenance"]["year"][0]["source_name"] == "IPDB"

    def test_get_model_404(self, client, db):
        resp = client.get("/api/models/nonexistent")
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
        assert "Design" in data["credits_by_role"]
        assert len(data["credits_by_role"]["Design"]) == 1
        assert data["credits_by_role"]["Design"][0]["model_name"] == "Medieval Madness"


class TestSourcesAPI:
    def test_list_sources(self, client, source):
        resp = client.get("/api/sources/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "IPDB"
