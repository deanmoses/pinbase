"""Tests for the kiosk page API at /api/pages/kiosk/{id}/."""

from __future__ import annotations

import pytest
from django.test import Client

from apps.catalog.models import Title
from apps.kiosk.models import KioskConfig, KioskConfigItem


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def title_a(db):
    return Title.objects.create(name="Medieval Madness", slug="medieval-madness-title")


def page_url(config_id: int) -> str:
    return f"/api/pages/kiosk/{config_id}/"


@pytest.mark.django_db
class TestKioskPage:
    def test_anon_can_fetch(self, client, title_a):
        cfg = KioskConfig.objects.create(page_heading="Welcome")
        KioskConfigItem.objects.create(
            config=cfg, title=title_a, position=1, hook="Try this!"
        )
        resp = client.get(page_url(cfg.pk))
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == cfg.pk
        assert body["page_heading"] == "Welcome"
        assert body["idle_seconds"] == 180
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["position"] == 1
        assert item["hook"] == "Try this!"
        assert item["title"]["slug"] == title_a.slug
        assert item["title"]["name"] == title_a.name
        # No machine_models attached → manufacturer/year/thumbnail all None.
        assert item["title"]["manufacturer"] is None
        assert item["title"]["year"] is None
        assert item["title"]["thumbnail_url"] is None

    def test_missing_returns_404(self, client):
        assert client.get(page_url(999_999)).status_code == 404

    def test_items_ordered_by_position(self, client):
        t1 = Title.objects.create(name="One", slug="one-title")
        t2 = Title.objects.create(name="Two", slug="two-title")
        t3 = Title.objects.create(name="Three", slug="three-title")
        cfg = KioskConfig.objects.create()
        # Insert out of order; the response must come back sorted by position.
        KioskConfigItem.objects.create(config=cfg, title=t3, position=3)
        KioskConfigItem.objects.create(config=cfg, title=t1, position=1)
        KioskConfigItem.objects.create(config=cfg, title=t2, position=2)
        resp = client.get(page_url(cfg.pk))
        assert resp.status_code == 200
        positions = [item["position"] for item in resp.json()["items"]]
        assert positions == [1, 2, 3]

    def test_empty_config(self, client):
        cfg = KioskConfig.objects.create()
        resp = client.get(page_url(cfg.pk))
        assert resp.status_code == 200
        assert resp.json()["items"] == []
