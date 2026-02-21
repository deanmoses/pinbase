"""Tests for ClaimManager.bulk_assert_claims()."""

import pytest
from django.contrib.contenttypes.models import ContentType

from apps.catalog.models import MachineModel, Manufacturer
from apps.provenance.models import Claim, Source


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
    return MachineModel.objects.create(
        name="Medieval Madness", manufacturer=manufacturer, year=1997
    )


@pytest.fixture
def pm2(db, manufacturer):
    return MachineModel.objects.create(
        name="Monster Bash", manufacturer=manufacturer, year=1998
    )


@pytest.fixture
def ct_id(db):
    return ContentType.objects.get_for_model(MachineModel).pk


class TestBulkAssertClaimsCreate:
    """First run: no existing claims, everything is new."""

    def test_creates_all_claims(self, source, ct_id, pm1, pm2):
        pending = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1997
            ),
            Claim(
                content_type_id=ct_id,
                object_id=pm1.pk,
                field_name="name",
                value="Medieval Madness",
            ),
            Claim(
                content_type_id=ct_id, object_id=pm2.pk, field_name="year", value=1998
            ),
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending)

        assert stats["created"] == 3
        assert stats["unchanged"] == 0
        assert stats["superseded"] == 0
        assert stats["duplicates_removed"] == 0

        assert Claim.objects.filter(is_active=True, source=source).count() == 3

    def test_all_created_claims_are_active(self, source, ct_id, pm1):
        pending = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1997
            ),
        ]
        Claim.objects.bulk_assert_claims(source, pending)

        claim = pm1.claims.get(source=source, field_name="year", is_active=True)
        assert claim.value == 1997


class TestBulkAssertClaimsIdempotent:
    """Second run with same data: nothing should be written."""

    def test_unchanged_on_second_run(self, source, ct_id, pm1, pm2):
        pending = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1997
            ),
            Claim(
                content_type_id=ct_id, object_id=pm2.pk, field_name="year", value=1998
            ),
        ]
        Claim.objects.bulk_assert_claims(source, pending)

        pending2 = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1997
            ),
            Claim(
                content_type_id=ct_id, object_id=pm2.pk, field_name="year", value=1998
            ),
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending2)

        assert stats["created"] == 0
        assert stats["superseded"] == 0
        assert stats["unchanged"] == 2

        assert Claim.objects.filter(is_active=True, source=source).count() == 2
        assert Claim.objects.filter(is_active=False, source=source).count() == 0


class TestBulkAssertClaimsSupersede:
    """Changed values should deactivate old claims and create new ones."""

    def test_supersedes_changed_value(self, source, ct_id, pm1):
        pending1 = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1997
            )
        ]
        Claim.objects.bulk_assert_claims(source, pending1)

        pending2 = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1998
            )
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending2)

        assert stats["created"] == 1
        assert stats["superseded"] == 1
        assert stats["unchanged"] == 0

        assert (
            pm1.claims.filter(source=source, field_name="year", is_active=True).count()
            == 1
        )
        assert (
            pm1.claims.filter(source=source, field_name="year", is_active=False).count()
            == 1
        )

        active = pm1.claims.get(source=source, field_name="year", is_active=True)
        assert active.value == 1998

    def test_supersedes_changed_citation(self, source, ct_id, pm1):
        pending1 = [
            Claim(
                content_type_id=ct_id,
                object_id=pm1.pk,
                field_name="year",
                value=1997,
                citation="old",
            )
        ]
        Claim.objects.bulk_assert_claims(source, pending1)

        pending2 = [
            Claim(
                content_type_id=ct_id,
                object_id=pm1.pk,
                field_name="year",
                value=1997,
                citation="new",
            )
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending2)

        assert stats["created"] == 1
        assert stats["superseded"] == 1


class TestBulkAssertClaimsDeduplicate:
    """Duplicate (object_id, field_name) pairs: last-write-wins."""

    def test_deduplicates_pending(self, source, ct_id, pm1):
        pending = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1997
            ),
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1998
            ),
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending)

        assert stats["duplicates_removed"] == 1
        assert stats["created"] == 1

        active = pm1.claims.get(source=source, field_name="year", is_active=True)
        assert active.value == 1998

    def test_no_constraint_violation_on_duplicates(self, source, ct_id, pm1):
        pending = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="name", value="V1"
            ),
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="name", value="V2"
            ),
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="name", value="V3"
            ),
        ]
        stats = Claim.objects.bulk_assert_claims(source, pending)
        assert stats["duplicates_removed"] == 2
        assert (
            pm1.claims.filter(source=source, field_name="name", is_active=True).count()
            == 1
        )


class TestBulkAssertClaimsIsolation:
    """Claims from different sources should not interfere."""

    def test_does_not_touch_other_sources(self, source, other_source, ct_id, pm1):
        Claim.objects.assert_claim(pm1, "year", 1997, source=other_source)

        pending = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1998
            )
        ]
        Claim.objects.bulk_assert_claims(source, pending)

        other_claim = pm1.claims.get(
            source=other_source, field_name="year", is_active=True
        )
        assert other_claim.value == 1997

        this_claim = pm1.claims.get(source=source, field_name="year", is_active=True)
        assert this_claim.value == 1998


class TestBulkAssertClaimsSourceSet:
    """The source FK should be set by bulk_assert_claims."""

    def test_source_is_set_on_pending_claims(self, source, ct_id, pm1):
        pending = [
            Claim(
                content_type_id=ct_id, object_id=pm1.pk, field_name="year", value=1997
            )
        ]
        Claim.objects.bulk_assert_claims(source, pending)

        claim = pm1.claims.get(field_name="year", is_active=True)
        assert claim.source == source
