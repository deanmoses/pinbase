"""Tests for Claim.license write path — assert_claim, bulk_assert_claims, and admin."""

import pytest
from django.contrib.contenttypes.models import ContentType

from apps.core.models import License
from apps.provenance.models import Claim, Source


@pytest.fixture
def source():
    return Source.objects.create(name="Test", slug="test", priority=100)


@pytest.fixture
def cc_by_sa():
    return License.objects.get(slug="cc-by-sa-4-0")


@pytest.fixture
def not_allowed():
    return License.objects.get(slug="not-allowed")


@pytest.mark.django_db
class TestAssertClaimLicense:
    def test_assert_claim_with_license(self, source, cc_by_sa):
        from apps.catalog.models import Manufacturer

        mfr = Manufacturer.objects.create(name="Test", slug="test")
        claim = Claim.objects.assert_claim(
            mfr, "description", "text", source=source, license=cc_by_sa
        )
        assert claim.license == cc_by_sa

    def test_assert_claim_without_license(self, source):
        from apps.catalog.models import Manufacturer

        mfr = Manufacturer.objects.create(name="Test", slug="test")
        claim = Claim.objects.assert_claim(mfr, "description", "text", source=source)
        assert claim.license is None


@pytest.mark.django_db
class TestBulkAssertClaimsLicense:
    def test_license_change_detected(self, source, cc_by_sa, not_allowed):
        """Changing only the license on a claim should supersede the old one."""
        from django.contrib.contenttypes.models import ContentType

        from apps.catalog.models import Manufacturer

        mfr = Manufacturer.objects.create(name="Test", slug="test")
        ct_id = ContentType.objects.get_for_model(Manufacturer).pk

        # First: assert with cc_by_sa license.
        claim1 = Claim(
            content_type_id=ct_id,
            object_id=mfr.pk,
            field_name="description",
            value="text",
            license=cc_by_sa,
        )
        stats = Claim.objects.bulk_assert_claims(source, [claim1])
        assert stats["created"] == 1

        # Second: same value, different license.
        claim2 = Claim(
            content_type_id=ct_id,
            object_id=mfr.pk,
            field_name="description",
            value="text",
            license=not_allowed,
        )
        stats = Claim.objects.bulk_assert_claims(source, [claim2])
        assert stats["created"] == 1
        assert stats["superseded"] == 1

        # Verify the active claim has the new license.
        active = Claim.objects.get(
            content_type_id=ct_id,
            object_id=mfr.pk,
            field_name="description",
            is_active=True,
        )
        assert active.license == not_allowed

    def test_same_license_unchanged(self, source, cc_by_sa):
        """Re-asserting the same value+license should be a no-op."""
        from django.contrib.contenttypes.models import ContentType

        from apps.catalog.models import Manufacturer

        mfr = Manufacturer.objects.create(name="Test", slug="test")
        ct_id = ContentType.objects.get_for_model(Manufacturer).pk

        claim = Claim(
            content_type_id=ct_id,
            object_id=mfr.pk,
            field_name="description",
            value="text",
            license=cc_by_sa,
        )
        Claim.objects.bulk_assert_claims(source, [claim])

        # Re-assert identical claim.
        claim2 = Claim(
            content_type_id=ct_id,
            object_id=mfr.pk,
            field_name="description",
            value="text",
            license=cc_by_sa,
        )
        stats = Claim.objects.bulk_assert_claims(source, [claim2])
        assert stats["unchanged"] == 1
        assert stats["created"] == 0


@pytest.mark.django_db
class TestClaimAdminLicense:
    def test_admin_save_model_preserves_license(self, source, cc_by_sa):
        """Creating a claim via ClaimAdmin.save_model() should persist the license."""
        from apps.catalog.models import Manufacturer
        from apps.provenance.admin import ClaimAdmin

        mfr = Manufacturer.objects.create(name="Test", slug="test")
        ct = ContentType.objects.get_for_model(Manufacturer)

        # Simulate what the admin does: build an unsaved Claim, call save_model.
        obj = Claim(
            content_type=ct,
            object_id=mfr.pk,
            field_name="description",
            value="admin text",
            citation="",
            source=source,
            license=cc_by_sa,
        )
        admin_instance = ClaimAdmin(Claim, None)
        admin_instance.save_model(request=None, obj=obj, form=None, change=False)

        # The obj.pk should now point to the created claim.
        saved = Claim.objects.get(pk=obj.pk)
        assert saved.license == cc_by_sa
        assert saved.value == "admin text"

    def test_admin_save_model_user_claim(self, cc_by_sa):
        """Creating a user-authored claim via admin should work."""
        from django.contrib.auth import get_user_model

        from apps.catalog.models import Manufacturer
        from apps.provenance.admin import ClaimAdmin

        User = get_user_model()
        user = User.objects.create_user(username="admin_user", password="test")
        mfr = Manufacturer.objects.create(name="Test", slug="test")
        ct = ContentType.objects.get_for_model(Manufacturer)

        obj = Claim(
            content_type=ct,
            object_id=mfr.pk,
            field_name="description",
            value="user text",
            citation="",
            source=None,
            user=user,
            license=cc_by_sa,
        )
        admin_instance = ClaimAdmin(Claim, None)
        admin_instance.save_model(request=None, obj=obj, form=None, change=False)

        saved = Claim.objects.get(pk=obj.pk)
        assert saved.user == user
        assert saved.source is None
        assert saved.license == cc_by_sa

    def test_admin_save_model_preserves_claim_key(self, source):
        """Creating a claim with an explicit claim_key via admin should preserve it."""
        from apps.catalog.models import Manufacturer
        from apps.provenance.admin import ClaimAdmin

        mfr = Manufacturer.objects.create(name="Test", slug="test")
        ct = ContentType.objects.get_for_model(Manufacturer)

        obj = Claim(
            content_type=ct,
            object_id=mfr.pk,
            field_name="credit",
            claim_key="credit|person:pat-lawlor|role:design",
            value={"person_slug": "pat-lawlor", "role": "design", "exists": True},
            citation="",
            source=source,
        )
        admin_instance = ClaimAdmin(Claim, None)
        admin_instance.save_model(request=None, obj=obj, form=None, change=False)

        saved = Claim.objects.get(pk=obj.pk)
        assert saved.claim_key == "credit|person:pat-lawlor|role:design"
