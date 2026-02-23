"""Tests for award resolution (resolve_award, resolve_recipients)."""

import pytest

from apps.catalog.claims import build_relationship_claim
from apps.catalog.models import Award, AwardRecipient, Person
from apps.catalog.resolve import resolve_award, resolve_recipients
from apps.provenance.models import Claim, Source


@pytest.fixture
def source(db):
    return Source.objects.create(
        name="Wikidata", slug="wikidata", source_type="database", priority=75
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
    return Person.objects.create(name="Steve Ritchie", slug="steve-ritchie")


@pytest.fixture
def award(db):
    return Award.objects.create(name="Pinball Hall of Fame")


def _assert_recipient_claim(award, person_slug, year, source):
    claim_key, value = build_relationship_claim(
        "recipient", {"person_slug": person_slug, "year": year}
    )
    Claim.objects.assert_claim(
        award, "recipient", value, source=source, claim_key=claim_key
    )


class TestResolveRecipients:
    def test_basic_materialization(self, award, person, source):
        _assert_recipient_claim(award, "pat-lawlor", 2023, source)
        resolve_recipients(award)

        assert AwardRecipient.objects.filter(
            award=award, person=person, year=2023
        ).exists()

    def test_multiple_recipients(self, award, person, person2, source):
        _assert_recipient_claim(award, "pat-lawlor", 2023, source)
        _assert_recipient_claim(award, "steve-ritchie", 2022, source)
        resolve_recipients(award)

        assert AwardRecipient.objects.filter(award=award).count() == 2

    def test_null_year(self, award, person, source):
        _assert_recipient_claim(award, "pat-lawlor", None, source)
        resolve_recipients(award)

        ar = AwardRecipient.objects.get(award=award, person=person)
        assert ar.year is None

    def test_year_subsumption(self, award, person, source):
        """When a person has both specific-year and null-year claims, only specific year materializes."""
        _assert_recipient_claim(award, "pat-lawlor", 2023, source)
        _assert_recipient_claim(award, "pat-lawlor", None, source)
        resolve_recipients(award)

        recipients = list(AwardRecipient.objects.filter(award=award))
        assert len(recipients) == 1
        assert recipients[0].year == 2023

    def test_multiple_years_same_person(self, award, person, source):
        """A person can win an award in multiple years."""
        _assert_recipient_claim(award, "pat-lawlor", 2022, source)
        _assert_recipient_claim(award, "pat-lawlor", 2023, source)
        resolve_recipients(award)

        assert AwardRecipient.objects.filter(award=award, person=person).count() == 2

    def test_idempotent(self, award, person, source):
        _assert_recipient_claim(award, "pat-lawlor", 2023, source)
        resolve_recipients(award)
        resolve_recipients(award)

        assert AwardRecipient.objects.filter(award=award).count() == 1

    def test_removes_stale_recipients(self, award, person, person2, source):
        _assert_recipient_claim(award, "pat-lawlor", 2023, source)
        _assert_recipient_claim(award, "steve-ritchie", 2022, source)
        resolve_recipients(award)
        assert AwardRecipient.objects.filter(award=award).count() == 2

        # Deactivate one recipient claim.
        Claim.objects.filter(
            field_name="recipient", claim_key__contains="steve-ritchie"
        ).update(is_active=False)
        resolve_recipients(award)

        assert AwardRecipient.objects.filter(award=award).count() == 1

    def test_exists_false_dispute(self, award, person, source, high_source):
        _assert_recipient_claim(award, "pat-lawlor", 2023, source)
        resolve_recipients(award)
        assert AwardRecipient.objects.filter(award=award).count() == 1

        # Higher-priority source disputes.
        claim_key, value = build_relationship_claim(
            "recipient", {"person_slug": "pat-lawlor", "year": 2023}, exists=False
        )
        Claim.objects.assert_claim(
            award, "recipient", value, source=high_source, claim_key=claim_key
        )
        resolve_recipients(award)

        assert AwardRecipient.objects.filter(award=award).count() == 0

    def test_unresolved_slug_warning(self, award, source, caplog):
        _assert_recipient_claim(award, "nobody-here", 2023, source)
        resolve_recipients(award)

        assert AwardRecipient.objects.filter(award=award).count() == 0
        assert "Unresolved person slug" in caplog.text


class TestResolveAward:
    def test_scalar_fields(self, award, source):
        Claim.objects.assert_claim(award, "name", "Hall of Fame", source=source)
        Claim.objects.assert_claim(
            award, "description", "Prestigious award", source=source
        )
        Claim.objects.assert_claim(
            award, "image_urls", ["https://example.com/hof.jpg"], source=source
        )

        resolved = resolve_award(award)
        assert resolved.name == "Hall of Fame"
        assert resolved.description == "Prestigious award"
        assert resolved.image_urls == ["https://example.com/hof.jpg"]

    def test_scalar_and_recipients(self, award, person, source):
        Claim.objects.assert_claim(award, "name", "Hall of Fame", source=source)
        _assert_recipient_claim(award, "pat-lawlor", 2023, source)

        resolved = resolve_award(award)
        assert resolved.name == "Hall of Fame"
        assert AwardRecipient.objects.filter(award=award, person=person).exists()
