"""Tests for the awards API endpoints and awards on person detail."""

import pytest
from django.core.cache import cache
from django.test import Client

from apps.catalog.cache import AWARDS_ALL_KEY
from apps.catalog.models import (
    Award,
    AwardRecipient,
    DesignCredit,
    MachineModel,
    Manufacturer,
    Person,
)


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def person(db):
    return Person.objects.create(name="Pat Lawlor", slug="pat-lawlor")


@pytest.fixture
def person2(db):
    return Person.objects.create(name="Steve Ritchie", slug="steve-ritchie")


@pytest.fixture
def award(db):
    return Award.objects.create(
        name="Pinball Hall of Fame",
        slug="pinball-hall-of-fame",
        description="Prestigious award",
        image_urls=["https://example.com/hof.jpg"],
    )


@pytest.fixture
def award2(db):
    return Award.objects.create(
        name="Designer of the Year",
        slug="designer-of-the-year",
    )


class TestAwardsAPI:
    def test_list_awards(self, client, award, person):
        AwardRecipient.objects.create(award=award, person=person, year=2023)
        resp = client.get("/api/awards/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Pinball Hall of Fame"
        assert data["items"][0]["recipient_count"] == 1

    def test_list_awards_search(self, client, award, award2):
        resp = client.get("/api/awards/?search=Hall")
        data = resp.json()
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Pinball Hall of Fame"

    def test_list_all_awards(self, client, award, award2, person):
        cache.clear()
        AwardRecipient.objects.create(award=award, person=person, year=2023)
        resp = client.get("/api/awards/all/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Ordered by recipient_count desc.
        assert data[0]["name"] == "Pinball Hall of Fame"
        assert data[0]["recipient_count"] == 1
        assert data[1]["recipient_count"] == 0
        cache.clear()

    def test_list_all_awards_caches(self, client, award):
        cache.clear()
        resp1 = client.get("/api/awards/all/")
        assert resp1.status_code == 200
        assert cache.get(AWARDS_ALL_KEY) is not None

        resp2 = client.get("/api/awards/all/")
        assert resp2.json() == resp1.json()
        cache.clear()

    def test_get_award_detail(self, client, award, person, person2):
        AwardRecipient.objects.create(award=award, person=person, year=2023)
        AwardRecipient.objects.create(award=award, person=person2, year=2022)

        resp = client.get(f"/api/awards/{award.slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Pinball Hall of Fame"
        assert data["description"] == "Prestigious award"
        assert data["image_urls"] == ["https://example.com/hof.jpg"]
        assert len(data["recipients"]) == 2
        # Year desc ordering: 2023 first.
        assert data["recipients"][0]["year"] == 2023
        assert data["recipients"][0]["person_name"] == "Pat Lawlor"
        assert data["recipients"][1]["year"] == 2022

    def test_get_award_detail_null_year(self, client, award, person):
        AwardRecipient.objects.create(award=award, person=person, year=None)

        resp = client.get(f"/api/awards/{award.slug}")
        data = resp.json()
        assert len(data["recipients"]) == 1
        assert data["recipients"][0]["year"] is None

    def test_get_award_404(self, client, db):
        resp = client.get("/api/awards/nonexistent")
        assert resp.status_code == 404


class TestPersonDetailAwards:
    def test_person_detail_includes_awards(self, client, person, award, db):
        manufacturer = Manufacturer.objects.create(name="Williams")
        machine = MachineModel.objects.create(
            name="Medieval Madness",
            manufacturer=manufacturer,
            year=1997,
            machine_type="SS",
        )
        DesignCredit.objects.create(model=machine, person=person, role="design")
        AwardRecipient.objects.create(award=award, person=person, year=2023)

        resp = client.get(f"/api/people/{person.slug}")
        assert resp.status_code == 200
        data = resp.json()
        assert "awards" in data
        assert len(data["awards"]) == 1
        assert data["awards"][0]["award_name"] == "Pinball Hall of Fame"
        assert data["awards"][0]["award_slug"] == "pinball-hall-of-fame"
        assert data["awards"][0]["year"] == 2023

    def test_person_detail_no_awards(self, client, person, db):
        resp = client.get(f"/api/people/{person.slug}")
        data = resp.json()
        assert data["awards"] == []

    def test_person_detail_multiple_awards(self, client, person, award, award2, db):
        AwardRecipient.objects.create(award=award, person=person, year=2023)
        AwardRecipient.objects.create(award=award2, person=person, year=2022)

        resp = client.get(f"/api/people/{person.slug}")
        data = resp.json()
        assert len(data["awards"]) == 2
