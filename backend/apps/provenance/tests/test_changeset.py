"""Tests for the ChangeSet model and its integration with Claim."""

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Manufacturer
from apps.provenance.models import ChangeSet, Claim, Source

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create(username="editor")


@pytest.fixture
def mfr(db):
    return Manufacturer.objects.create(name="Williams", slug="williams")


@pytest.fixture
def source(db):
    return Source.objects.create(name="TestSource", slug="test-source", priority=10)


@pytest.mark.django_db
class TestChangeSetModel:
    def test_create_changeset(self, user):
        cs = ChangeSet.objects.create(user=user, note="Fixed description")
        assert cs.pk is not None
        assert cs.user == user
        assert cs.note == "Fixed description"
        assert cs.created_at is not None

    def test_changeset_without_note(self, user):
        cs = ChangeSet.objects.create(user=user)
        assert cs.note == ""

    def test_changeset_without_user(self):
        """ChangeSet with null user is allowed (future: source-level changesets)."""
        cs = ChangeSet.objects.create()
        assert cs.user is None


@pytest.mark.django_db
class TestChangeSetClaimGrouping:
    def test_claims_linked_to_changeset(self, user, mfr):
        cs = ChangeSet.objects.create(user=user, note="Updated fields")
        c1 = Claim.objects.assert_claim(
            mfr, "name", "Williams Electronics", user=user, changeset=cs
        )
        c2 = Claim.objects.assert_claim(
            mfr, "description", "Pinball manufacturer", user=user, changeset=cs
        )
        assert c1.changeset == cs
        assert c2.changeset == cs
        assert set(cs.claims.values_list("pk", flat=True)) == {c1.pk, c2.pk}

    def test_claim_without_changeset(self, user, mfr):
        """Claims without a changeset still work (backwards compatible)."""
        claim = Claim.objects.assert_claim(mfr, "name", "Williams", user=user)
        assert claim.changeset is None

    def test_source_claim_with_changeset_rejected(self, source, mfr, user):
        """Source-attributed claims cannot use ChangeSets (not yet designed)."""
        cs = ChangeSet.objects.create(user=user)
        with pytest.raises(ValueError, match="Source-attributed claims"):
            Claim.objects.assert_claim(
                mfr, "name", "Williams", source=source, changeset=cs
            )

    def test_changeset_user_mismatch_rejected(self, user, mfr):
        """ChangeSet user must match the claim user."""
        other_user = User.objects.create(username="other")
        cs = ChangeSet.objects.create(user=other_user)
        with pytest.raises(ValueError, match="must match"):
            Claim.objects.assert_claim(mfr, "name", "Williams", user=user, changeset=cs)

    def test_changeset_survives_claim_superseding(self, user, mfr):
        """When a claim is superseded, the old claim keeps its changeset link."""
        cs1 = ChangeSet.objects.create(user=user, note="First edit")
        c1 = Claim.objects.assert_claim(
            mfr, "description", "First", user=user, changeset=cs1
        )

        cs2 = ChangeSet.objects.create(user=user, note="Second edit")
        c2 = Claim.objects.assert_claim(
            mfr, "description", "Second", user=user, changeset=cs2
        )

        c1.refresh_from_db()
        assert c1.is_active is False
        assert c1.changeset == cs1
        assert c2.is_active is True
        assert c2.changeset == cs2
