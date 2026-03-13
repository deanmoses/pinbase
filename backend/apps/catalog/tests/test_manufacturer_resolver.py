"""Tests for ManufacturerResolver shared utility."""

from __future__ import annotations

import pytest

from apps.catalog.ingestion.bulk_utils import ManufacturerResolver
from apps.catalog.models import CorporateEntity, Manufacturer


@pytest.mark.django_db
class TestManufacturerResolver:
    def test_resolve_by_name(self):
        Manufacturer.objects.create(name="Williams", slug="williams")
        resolver = ManufacturerResolver()
        assert resolver.resolve("Williams") == "williams"

    def test_resolve_by_trade_name(self):
        Manufacturer.objects.create(
            name="Midway Manufacturing", slug="bally", trade_name="Bally"
        )
        resolver = ManufacturerResolver()
        assert resolver.resolve("Bally") == "bally"

    def test_resolve_case_insensitive(self):
        Manufacturer.objects.create(name="Gottlieb", slug="gottlieb")
        resolver = ManufacturerResolver()
        assert resolver.resolve("GOTTLIEB") == "gottlieb"
        assert resolver.resolve("gottlieb") == "gottlieb"

    def test_resolve_unknown_returns_none(self):
        resolver = ManufacturerResolver()
        assert resolver.resolve("Nonexistent") is None

    def test_resolve_entity(self):
        mfr = Manufacturer.objects.create(name="Williams", slug="williams")
        CorporateEntity.objects.create(
            name="Williams Electronic Games",
            manufacturer=mfr,
        )
        resolver = ManufacturerResolver()
        assert resolver.resolve_entity("Williams Electronic Games") == "williams"

    def test_resolve_entity_unknown_returns_none(self):
        resolver = ManufacturerResolver()
        assert resolver.resolve_entity("Nonexistent Corp") is None

    def test_resolve_or_create_existing(self):
        Manufacturer.objects.create(name="Stern", slug="stern")
        resolver = ManufacturerResolver()
        assert resolver.resolve_or_create("Stern") == "stern"
        # No new manufacturer created.
        assert Manufacturer.objects.count() == 1

    def test_resolve_or_create_new(self):
        resolver = ManufacturerResolver()
        slug = resolver.resolve_or_create("Jersey Jack", trade_name="JJP")
        assert slug == "jersey-jack"
        mfr = Manufacturer.objects.get(slug=slug)
        assert mfr.name == "Jersey Jack"
        assert mfr.trade_name == "JJP"

    def test_resolve_or_create_caches_result(self):
        resolver = ManufacturerResolver()
        slug1 = resolver.resolve_or_create("Spooky Pinball")
        slug2 = resolver.resolve_or_create("Spooky Pinball")
        assert slug1 == slug2
        assert Manufacturer.objects.filter(name="Spooky Pinball").count() == 1

    def test_resolve_or_create_caches_trade_name(self):
        resolver = ManufacturerResolver()
        resolver.resolve_or_create("Some Company", trade_name="TradeCo")
        assert resolver.resolve("TradeCo") == "some-company"

    def test_resolve_or_create_handles_slug_collision(self):
        Manufacturer.objects.create(name="Acme", slug="acme")
        resolver = ManufacturerResolver()
        # Creating another "Acme" should get a unique slug.
        slug = resolver.resolve_or_create("Acme Corp")
        assert slug != "acme"
        assert Manufacturer.objects.count() == 2
