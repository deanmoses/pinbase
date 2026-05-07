import pytest
from django.db import IntegrityError

from apps.accounts.models import User


@pytest.mark.django_db
class TestUserDefaults:
    def test_default_priority(self):
        user = User.objects.create_user(email="testuser@example.com")
        assert user.priority == 10000

    def test_priority_is_configurable(self):
        user = User.objects.create_user(email="editor@example.com")
        user.priority = 200
        user.save()
        user.refresh_from_db()
        assert user.priority == 200

    def test_username_derived_from_email(self):
        user = User.objects.create_user(email="Alice.Smith+tag@example.com")
        # local-part lowercased, ./_/+ → -, collapsed
        assert user.username == "alice-smith-tag"

    def test_create_user_resolves_username_collision(self):
        """Two users with the same local-part across different domains."""
        u1 = User.objects.create_user(email="same@example.com")
        u2 = User.objects.create_user(email="same@other.com")
        assert u1.username == "same"
        assert u2.username == "same-1"


@pytest.mark.django_db
class TestNaturalKeyLookup:
    """Password login (ModelBackend) goes through get_by_natural_key."""

    def test_get_by_natural_key_is_case_insensitive(self):
        user = User.objects.create_user(email="MixedCase@example.com")
        assert User.objects.get_by_natural_key("MixedCase@example.com") == user
        assert User.objects.get_by_natural_key("mixedcase@example.com") == user
        assert User.objects.get_by_natural_key("MIXEDCASE@EXAMPLE.COM") == user

    def test_authenticate_is_case_insensitive(self):
        from django.contrib.auth import authenticate

        password = "secret123"  # noqa: S105  # pragma: allowlist secret
        User.objects.create_user(email="MixedCase@example.com", password=password)
        assert (
            authenticate(username="mixedcase@example.com", password=password)
            is not None
        )


@pytest.mark.django_db
class TestEmailUniqueness:
    def test_case_insensitive_unique(self):
        User.objects.create_user(email="alice@example.com")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="ALICE@example.com")

    def test_email_casing_preserved(self):
        user = User.objects.create_user(email="Alice@Example.com")
        # normalize_email lowercases the domain only
        assert user.email == "Alice@example.com"


@pytest.mark.django_db
class TestWorkOSFields:
    def test_workos_user_id_default_null(self):
        user = User.objects.create_user(email="testuser@example.com")
        assert user.workos_user_id is None

    def test_workos_user_id_uniqueness(self):
        User.objects.create_user(email="user1@example.com", workos_user_id="user_01ABC")
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email="user2@example.com", workos_user_id="user_01ABC"
            )

    def test_multiple_null_workos_user_id_allowed(self):
        User.objects.create_user(email="legacy1@example.com")
        User.objects.create_user(email="legacy2@example.com")
        assert User.objects.filter(workos_user_id=None).count() >= 2
