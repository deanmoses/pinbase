"""Tests for provenance helpers: active_claims() and citation_instances()."""

import pytest

from apps.catalog.models import Series
from apps.provenance.helpers import (
    active_claims,
    citation_instances,
    claims_prefetch,
)
from apps.provenance.models import Claim, Source


@pytest.fixture
def source():
    return Source.objects.create(
        name="Test", slug="test", source_type="database", priority=100
    )


@pytest.mark.django_db
class TestActiveClaims:
    def test_returns_list_when_prefetched(self, source):
        series = Series.objects.create(slug="s", name="S")
        Claim.objects.assert_claim(series, "name", "S", source=source)

        loaded = Series.objects.prefetch_related(claims_prefetch()).get(pk=series.pk)

        claims = active_claims(loaded)
        assert isinstance(claims, list)
        assert {c.field_name for c in claims} == {"name"}

    def test_raises_when_not_prefetched(self):
        series = Series.objects.create(slug="s", name="S")

        with pytest.raises(AssertionError, match="claims_prefetch"):
            active_claims(series)


@pytest.mark.django_db
class TestCitationInstances:
    def test_returns_list_when_prefetched(self, source):
        series = Series.objects.create(slug="s", name="S")
        Claim.objects.assert_claim(series, "name", "S", source=source)

        loaded = Series.objects.prefetch_related(claims_prefetch()).get(pk=series.pk)
        claim = active_claims(loaded)[0]

        instances = citation_instances(claim)
        assert isinstance(instances, list)

    def test_raises_when_claim_not_prefetched(self, source):
        series = Series.objects.create(slug="s", name="S")
        Claim.objects.assert_claim(series, "name", "S", source=source)
        bare_claim = Claim.objects.get(object_id=series.pk, field_name="name")

        with pytest.raises(AssertionError, match="claims_prefetch"):
            citation_instances(bare_claim)
