"""Tests for ClaimManager.bulk_assert_claims()."""

import pytest

from apps.machines.models import Claim, Manufacturer, PinballModel, Source


@pytest.fixture
def source(db):
    return Source.objects.create(
        name="IPDB", slug="ipdb", source_type="database", priority=10
    )


@pytest.fixture
def other_source(db):
    return Source.objects.create(
        name="OPDB", slug="opdb", source_type="database", priority=20
    )


@pytest.fixture
def manufacturer(db):
    return Manufacturer.objects.create(name="Williams")


@pytest.fixture
def pm1(db, manufacturer):
    return PinballModel.objects.create(
        name="Medieval Madness", manufacturer=manufacturer, year=1997
    )


@pytest.fixture
def pm2(db, manufacturer):
    return PinballModel.objects.create(
        name="Monster Bash", manufacturer=manufacturer, year=1998
    )


class TestBulkAssertClaimsCreate:
    """First run: no existing claims, everything is new."""

    def test_creates_all_claims(self, source, pm1, pm2):
        pending = [
            Claim(model_id=pm1.pk, field_name="year", value=1997),
            Claim(model_id=pm1.pk, field_name="name", value="Medieval Madness"),
            Claim(model_id=pm2.pk, field_name="year", value=1998),
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending)

        assert stats["created"] == 3
        assert stats["unchanged"] == 0
        assert stats["superseded"] == 0
        assert stats["duplicates_removed"] == 0

        assert Claim.objects.filter(is_active=True, source=source).count() == 3

    def test_all_created_claims_are_active(self, source, pm1):
        pending = [
            Claim(model_id=pm1.pk, field_name="year", value=1997),
        ]
        Claim.objects.bulk_assert_claims(source, pending)

        claim = Claim.objects.get(
            model=pm1, source=source, field_name="year", is_active=True
        )
        assert claim.value == 1997


class TestBulkAssertClaimsIdempotent:
    """Second run with same data: nothing should be written."""

    def test_unchanged_on_second_run(self, source, pm1, pm2):
        pending = [
            Claim(model_id=pm1.pk, field_name="year", value=1997),
            Claim(model_id=pm2.pk, field_name="year", value=1998),
        ]
        Claim.objects.bulk_assert_claims(source, pending)

        # Run again with identical data.
        pending2 = [
            Claim(model_id=pm1.pk, field_name="year", value=1997),
            Claim(model_id=pm2.pk, field_name="year", value=1998),
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending2)

        assert stats["created"] == 0
        assert stats["superseded"] == 0
        assert stats["unchanged"] == 2

        # Still only 2 active claims, no extras.
        assert Claim.objects.filter(is_active=True, source=source).count() == 2
        # No deactivated claims (nothing was superseded).
        assert Claim.objects.filter(is_active=False, source=source).count() == 0


class TestBulkAssertClaimsSupersede:
    """Changed values should deactivate old claims and create new ones."""

    def test_supersedes_changed_value(self, source, pm1):
        pending1 = [Claim(model_id=pm1.pk, field_name="year", value=1997)]
        Claim.objects.bulk_assert_claims(source, pending1)

        pending2 = [Claim(model_id=pm1.pk, field_name="year", value=1998)]
        stats = Claim.objects.bulk_assert_claims(source, pending2)

        assert stats["created"] == 1
        assert stats["superseded"] == 1
        assert stats["unchanged"] == 0

        # One active, one deactivated.
        assert (
            Claim.objects.filter(
                model=pm1, source=source, field_name="year", is_active=True
            ).count()
            == 1
        )
        assert (
            Claim.objects.filter(
                model=pm1, source=source, field_name="year", is_active=False
            ).count()
            == 1
        )

        # Active claim has the new value.
        active = Claim.objects.get(
            model=pm1, source=source, field_name="year", is_active=True
        )
        assert active.value == 1998

    def test_supersedes_changed_citation(self, source, pm1):
        pending1 = [
            Claim(model_id=pm1.pk, field_name="year", value=1997, citation="old")
        ]
        Claim.objects.bulk_assert_claims(source, pending1)

        pending2 = [
            Claim(model_id=pm1.pk, field_name="year", value=1997, citation="new")
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending2)

        assert stats["created"] == 1
        assert stats["superseded"] == 1


class TestBulkAssertClaimsDeduplicate:
    """Duplicate (model_id, field_name) pairs: last-write-wins."""

    def test_deduplicates_pending(self, source, pm1):
        pending = [
            Claim(model_id=pm1.pk, field_name="year", value=1997),
            Claim(model_id=pm1.pk, field_name="year", value=1998),  # Should win
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending)

        assert stats["duplicates_removed"] == 1
        assert stats["created"] == 1

        active = Claim.objects.get(
            model=pm1, source=source, field_name="year", is_active=True
        )
        assert active.value == 1998

    def test_no_constraint_violation_on_duplicates(self, source, pm1):
        """Duplicates should not cause IntegrityError."""
        pending = [
            Claim(model_id=pm1.pk, field_name="name", value="V1"),
            Claim(model_id=pm1.pk, field_name="name", value="V2"),
            Claim(model_id=pm1.pk, field_name="name", value="V3"),
        ]
        # Should not raise.
        stats = Claim.objects.bulk_assert_claims(source, pending)
        assert stats["duplicates_removed"] == 2
        assert (
            Claim.objects.filter(
                model=pm1, source=source, field_name="name", is_active=True
            ).count()
            == 1
        )


class TestBulkAssertClaimsIsolation:
    """Claims from different sources should not interfere."""

    def test_does_not_touch_other_sources(self, source, other_source, pm1):
        # Set up claims from both sources.
        Claim.objects.assert_claim(pm1, "year", 1997, source=other_source)

        pending = [Claim(model_id=pm1.pk, field_name="year", value=1998)]
        Claim.objects.bulk_assert_claims(source, pending)

        # Other source's claim is untouched.
        other_claim = Claim.objects.get(
            model=pm1, source=other_source, field_name="year", is_active=True
        )
        assert other_claim.value == 1997

        # This source's claim is also active.
        this_claim = Claim.objects.get(
            model=pm1, source=source, field_name="year", is_active=True
        )
        assert this_claim.value == 1998


class TestBulkAssertClaimsSourceSet:
    """The source FK should be set by bulk_assert_claims."""

    def test_source_is_set_on_pending_claims(self, source, pm1):
        pending = [Claim(model_id=pm1.pk, field_name="year", value=1997)]
        Claim.objects.bulk_assert_claims(source, pending)

        claim = Claim.objects.get(model=pm1, field_name="year", is_active=True)
        assert claim.source == source
