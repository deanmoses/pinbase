"""Tests for credit claim resolution (resolve_credits)."""

import pytest

from apps.catalog.claims import build_relationship_claim
from apps.catalog.models import DesignCredit, MachineModel, Person
from apps.catalog.resolve import resolve_credits
from apps.provenance.models import Claim, Source


@pytest.fixture
def source(db):
    return Source.objects.create(
        name="IPDB", slug="ipdb", source_type="database", priority=10
    )


@pytest.fixture
def high_source(db):
    return Source.objects.create(
        name="Editorial", slug="editorial", source_type="editorial", priority=100
    )


@pytest.fixture
def person(db):
    return Person.objects.create(name="Pat Lawlor", slug="pat-lawlor")


@pytest.fixture
def person2(db):
    return Person.objects.create(name="John Youssi", slug="john-youssi")


@pytest.fixture
def machine(db):
    return MachineModel.objects.create(name="Medieval Madness")


def _assert_credit_claim(machine, person_slug, role, source):
    """Helper to create a credit claim via the manager."""
    claim_key, value = build_relationship_claim(
        "credit", {"person_slug": person_slug, "role": role}
    )
    Claim.objects.assert_claim(
        machine, "credit", value, source=source, claim_key=claim_key
    )


class TestResolveCredits:
    def test_basic_materialization(self, machine, person, source):
        _assert_credit_claim(machine, "pat-lawlor", "design", source)
        resolve_credits(machine)

        assert DesignCredit.objects.filter(
            model=machine, person=person, role="design"
        ).exists()

    def test_multiple_credits(self, machine, person, person2, source):
        _assert_credit_claim(machine, "pat-lawlor", "design", source)
        _assert_credit_claim(machine, "john-youssi", "art", source)
        resolve_credits(machine)

        assert DesignCredit.objects.filter(model=machine).count() == 2
        assert DesignCredit.objects.filter(
            model=machine, person=person, role="design"
        ).exists()
        assert DesignCredit.objects.filter(
            model=machine, person=person2, role="art"
        ).exists()

    def test_idempotent(self, machine, person, source):
        _assert_credit_claim(machine, "pat-lawlor", "design", source)
        resolve_credits(machine)
        resolve_credits(machine)

        assert DesignCredit.objects.filter(model=machine).count() == 1

    def test_removes_stale_credits(self, machine, person, person2, source):
        """If a credit claim is deactivated, resolution removes the DesignCredit."""
        _assert_credit_claim(machine, "pat-lawlor", "design", source)
        _assert_credit_claim(machine, "john-youssi", "art", source)
        resolve_credits(machine)
        assert DesignCredit.objects.filter(model=machine).count() == 2

        # Deactivate the art credit claim.
        Claim.objects.filter(
            field_name="credit", claim_key__contains="john-youssi"
        ).update(is_active=False)
        resolve_credits(machine)

        assert DesignCredit.objects.filter(model=machine).count() == 1
        assert not DesignCredit.objects.filter(model=machine, person=person2).exists()

    def test_exists_false_dispute(self, machine, person, source, high_source):
        """A higher-priority exists=False claim prevents materialization."""
        _assert_credit_claim(machine, "pat-lawlor", "design", source)
        resolve_credits(machine)
        assert DesignCredit.objects.filter(model=machine).count() == 1

        # Higher-priority source disputes the credit.
        claim_key, value = build_relationship_claim(
            "credit", {"person_slug": "pat-lawlor", "role": "design"}, exists=False
        )
        Claim.objects.assert_claim(
            machine, "credit", value, source=high_source, claim_key=claim_key
        )
        resolve_credits(machine)

        assert DesignCredit.objects.filter(model=machine).count() == 0

    def test_multi_source_union(self, machine, person, person2, source, high_source):
        """Credits from multiple sources are unioned (each claim_key is independent)."""
        _assert_credit_claim(machine, "pat-lawlor", "design", source)
        claim_key, value = build_relationship_claim(
            "credit", {"person_slug": "john-youssi", "role": "art"}
        )
        Claim.objects.assert_claim(
            machine, "credit", value, source=high_source, claim_key=claim_key
        )
        resolve_credits(machine)

        assert DesignCredit.objects.filter(model=machine).count() == 2

    def test_unresolved_slug_warning(self, machine, source, caplog):
        """Credit claim for a non-existent person slug logs a warning."""
        _assert_credit_claim(machine, "nobody-here", "design", source)
        resolve_credits(machine)

        assert DesignCredit.objects.filter(model=machine).count() == 0
        assert "Unresolved person slug" in caplog.text
