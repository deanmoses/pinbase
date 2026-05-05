"""Constraint and behavior tests for KioskConfig and KioskConfigItem."""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.catalog.models import Title
from apps.kiosk.models import KioskConfig, KioskConfigItem


@pytest.fixture
def title_a(db):
    return Title.objects.create(name="Medieval Madness", slug="medieval-madness-title")


@pytest.fixture
def title_b(db):
    return Title.objects.create(name="Attack from Mars", slug="attack-from-mars-title")


@pytest.fixture
def kiosk(db):
    return KioskConfig.objects.create(name="Lobby kiosk")


class TestKioskConfigDefaults:
    def test_defaults(self, kiosk):
        assert kiosk.name == "Lobby kiosk"
        assert kiosk.page_heading == ""
        assert kiosk.idle_seconds == 180

    def test_str(self, kiosk):
        assert str(kiosk) == "Lobby kiosk"


class TestKioskConfigConstraints:
    def test_blank_name_rejected(self, db):
        with pytest.raises(IntegrityError):
            KioskConfig.objects.create(name="")

    def test_blank_page_heading_accepted(self, db):
        # Operators can clear the H1 — no field_not_blank on page_heading.
        cfg = KioskConfig.objects.create(name="Headless kiosk", page_heading="")
        assert cfg.page_heading == ""

    def test_duplicate_name_rejected(self, db):
        KioskConfig.objects.create(name="Lobby kiosk")
        with pytest.raises(IntegrityError):
            KioskConfig.objects.create(name="Lobby kiosk")

    @pytest.mark.parametrize("bad", [9, 3601])
    def test_idle_seconds_out_of_range_rejected(self, db, bad):
        with pytest.raises(IntegrityError):
            KioskConfig.objects.create(name=f"Bad-{bad}", idle_seconds=bad)

    @pytest.mark.parametrize("ok", [10, 3600])
    def test_idle_seconds_boundaries_accepted(self, db, ok):
        cfg = KioskConfig.objects.create(name=f"Ok-{ok}", idle_seconds=ok)
        assert cfg.idle_seconds == ok


class TestKioskConfigItemStr:
    def test_str(self, db, kiosk, title_a):
        item = KioskConfigItem.objects.create(config=kiosk, title=title_a, position=1)
        assert str(item) == "Lobby kiosk #1: Medieval Madness"


class TestKioskConfigItemConstraints:
    def test_duplicate_position_rejected(self, db, kiosk, title_a, title_b):
        KioskConfigItem.objects.create(config=kiosk, title=title_a, position=1)
        with pytest.raises(IntegrityError):
            KioskConfigItem.objects.create(config=kiosk, title=title_b, position=1)

    def test_duplicate_title_rejected(self, db, kiosk, title_a):
        KioskConfigItem.objects.create(config=kiosk, title=title_a, position=1)
        with pytest.raises(IntegrityError):
            KioskConfigItem.objects.create(config=kiosk, title=title_a, position=2)

    def test_same_position_allowed_across_configs(self, db, title_a, title_b):
        c1 = KioskConfig.objects.create(name="K1")
        c2 = KioskConfig.objects.create(name="K2")
        KioskConfigItem.objects.create(config=c1, title=title_a, position=1)
        # Same position (1) and same title are both fine in a different config.
        KioskConfigItem.objects.create(config=c2, title=title_a, position=1)
        KioskConfigItem.objects.create(config=c1, title=title_b, position=2)

    def test_deleting_title_cascades_item(self, db, kiosk, title_a):
        item = KioskConfigItem.objects.create(config=kiosk, title=title_a, position=1)
        title_a.delete()
        assert not KioskConfigItem.objects.filter(pk=item.pk).exists()

    def test_deleting_config_cascades_items(self, db, kiosk, title_a, title_b):
        KioskConfigItem.objects.create(config=kiosk, title=title_a, position=1)
        KioskConfigItem.objects.create(config=kiosk, title=title_b, position=2)
        kiosk.delete()
        assert KioskConfigItem.objects.count() == 0

    def test_ordering(self, db, kiosk, title_a, title_b):
        KioskConfigItem.objects.create(config=kiosk, title=title_b, position=2)
        KioskConfigItem.objects.create(config=kiosk, title=title_a, position=1)
        positions = list(kiosk.items.values_list("position", flat=True))
        assert positions == [1, 2]


class TestAtomicityOfConstraintFailures:
    """Confirm that violations raise IntegrityError without leaving partial state."""

    def test_unique_violation_does_not_persist(self, db, kiosk, title_a):
        KioskConfigItem.objects.create(config=kiosk, title=title_a, position=1)
        with pytest.raises(IntegrityError), transaction.atomic():
            KioskConfigItem.objects.create(config=kiosk, title=title_a, position=2)
        assert kiosk.items.count() == 1
