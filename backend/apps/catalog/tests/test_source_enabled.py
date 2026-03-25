"""Tests for Source.is_enabled filtering in claim resolution."""

import pytest

from apps.catalog.claims import build_relationship_claim
from apps.catalog.models import (
    CreditRole,
    MachineModel,
    Manufacturer,
    Person,
    Theme,
    Title,
)
from apps.core.models import get_claim_fields
from apps.catalog.resolve import (
    _resolve_bulk,
    resolve_entity,
    resolve_themes,
)
from apps.catalog.resolve._relationships import resolve_all_credits
from apps.provenance.models import Claim, Source


@pytest.fixture
def source_a():
    return Source.objects.create(
        name="Source A", slug="source-a", source_type="database", priority=100
    )


@pytest.fixture
def source_b():
    return Source.objects.create(
        name="Source B", slug="source-b", source_type="editorial", priority=200
    )


@pytest.mark.django_db
class TestIsEnabledResolveSingle:
    def test_disabled_source_excluded_from_resolution(self, source_a):
        """Claims from a disabled source should not participate in resolution."""
        mfr = Manufacturer.objects.create(name="", slug="test-mfr")
        Claim.objects.assert_claim(mfr, "name", "From Disabled", source=source_a)

        source_a.is_enabled = False
        source_a.save()

        resolve_entity(mfr)
        mfr.refresh_from_db()
        assert mfr.name == ""

    def test_disabled_source_fallback_to_enabled(self, source_a, source_b):
        """When the higher-priority source is disabled, the lower-priority one wins."""
        mfr = Manufacturer.objects.create(name="", slug="test-mfr")
        Claim.objects.assert_claim(mfr, "name", "Low Priority", source=source_a)
        Claim.objects.assert_claim(mfr, "name", "High Priority", source=source_b)

        # With both enabled, source_b wins (priority 200 > 100).
        resolve_entity(mfr)
        mfr.refresh_from_db()
        assert mfr.name == "High Priority"

        # Disable source_b; source_a should now win.
        source_b.is_enabled = False
        source_b.save()

        resolve_entity(mfr)
        mfr.refresh_from_db()
        assert mfr.name == "Low Priority"


@pytest.mark.django_db
class TestIsEnabledResolveBulk:
    def test_disabled_source_excluded_from_bulk_resolution(self, source_a):
        """Bulk resolution should skip claims from disabled sources."""
        t = Title.objects.create(opdb_id="G1", name="", slug="t1")
        Claim.objects.assert_claim(t, "name", "From Disabled", source=source_a)

        source_a.is_enabled = False
        source_a.save()

        _resolve_bulk(Title, get_claim_fields(Title))

        t.refresh_from_db()
        assert t.name == ""

    def test_bulk_fallback_when_winner_disabled(self, source_a, source_b):
        """Bulk resolution falls back to enabled source when winner is disabled."""
        t = Title.objects.create(opdb_id="G1", name="", slug="t1")
        Claim.objects.assert_claim(t, "name", "Low Priority", source=source_a)
        Claim.objects.assert_claim(t, "name", "High Priority", source=source_b)

        source_b.is_enabled = False
        source_b.save()

        _resolve_bulk(Title, get_claim_fields(Title))

        t.refresh_from_db()
        assert t.name == "Low Priority"


@pytest.mark.django_db
class TestIsEnabledUserClaims:
    def test_user_claims_unaffected_by_source_enabled(self, source_a):
        """User claims (source=None) should not be filtered by is_enabled."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="testuser", password="test")

        mfr = Manufacturer.objects.create(name="", slug="test-mfr")
        Claim.objects.assert_claim(mfr, "name", "User Claim", user=user)

        # Disable source_a (irrelevant — the claim is user-owned, not source-owned).
        source_a.is_enabled = False
        source_a.save()

        resolve_entity(mfr)
        mfr.refresh_from_db()
        assert mfr.name == "User Claim"


@pytest.mark.django_db
class TestIsEnabledRelationshipResolution:
    def test_disabled_source_theme_excluded(self, source_a):
        """Theme claims from a disabled source should not materialize."""
        theme = Theme.objects.create(name="Medieval", slug="medieval")
        pm = MachineModel.objects.create(name="Test", slug="test-pm")

        claim_key, value = build_relationship_claim("theme", {"theme_slug": "medieval"})
        Claim.objects.assert_claim(
            pm,
            "theme",
            value,
            source=source_a,
            claim_key=claim_key,
        )

        # With source enabled, theme should resolve.
        resolve_themes(pm)
        assert theme in pm.themes.all()

        # Disable source; theme should be removed.
        source_a.is_enabled = False
        source_a.save()

        resolve_themes(pm)
        assert theme not in pm.themes.all()

    def test_disabled_source_credit_excluded(self, source_a):
        """Credit claims from a disabled source should not materialize."""
        role = CreditRole.objects.create(name="Design", slug="design")
        person = Person.objects.create(name="Pat Lawlor", slug="pat-lawlor")
        pm = MachineModel.objects.create(name="Test", slug="test-pm")

        claim_key, value = build_relationship_claim(
            "credit", {"person_slug": "pat-lawlor", "role": "design"}
        )
        Claim.objects.assert_claim(
            pm,
            "credit",
            value,
            source=source_a,
            claim_key=claim_key,
        )

        # With source enabled, credit should resolve.
        resolve_all_credits([pm])
        assert pm.credits.filter(person=person, role=role).exists()

        # Disable source; credit should be removed.
        source_a.is_enabled = False
        source_a.save()

        resolve_all_credits([pm])
        assert not pm.credits.filter(person=person, role=role).exists()


@pytest.mark.django_db
class TestIsEnabledActivityPrefetch:
    def test_claims_prefetch_excludes_disabled_source(self, source_a, source_b):
        """_claims_prefetch() should not include claims from disabled sources."""
        from apps.catalog.api.helpers import _claims_prefetch

        mfr = Manufacturer.objects.create(name="", slug="test-mfr")
        Claim.objects.assert_claim(mfr, "name", "From A", source=source_a)
        Claim.objects.assert_claim(mfr, "description", "From B", source=source_b)

        source_a.is_enabled = False
        source_a.save()

        prefetched = Manufacturer.objects.prefetch_related(_claims_prefetch()).get(
            pk=mfr.pk
        )

        claims = prefetched.active_claims
        source_slugs = {c.source.slug for c in claims if c.source}
        assert "source-a" not in source_slugs
        assert "source-b" in source_slugs
