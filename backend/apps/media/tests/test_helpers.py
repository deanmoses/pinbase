"""Tests for media helpers: all_media() and primary_media()."""

from __future__ import annotations

import pytest

from apps.catalog.tests.conftest import make_machine_model
from apps.media.helpers import all_media, primary_media

pytestmark = pytest.mark.django_db


class TestAllMedia:
    def test_returns_list_when_prefetched(self):
        pm = make_machine_model(name="X", slug="x")
        pm.all_media = []  # simulate _media_prefetch() attaching the attr

        assert all_media(pm) == []

    def test_raises_when_not_prefetched(self):
        pm = make_machine_model(name="X", slug="x")

        with pytest.raises(AssertionError, match="_media_prefetch"):
            all_media(pm)


class TestPrimaryMedia:
    def test_returns_list_when_prefetched(self):
        pm = make_machine_model(name="X", slug="x")
        pm.primary_media = []

        assert primary_media(pm) == []

    def test_raises_when_not_prefetched(self):
        pm = make_machine_model(name="X", slug="x")

        with pytest.raises(AssertionError, match="primary_media"):
            primary_media(pm)
