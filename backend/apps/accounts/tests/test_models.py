import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestUserProfileAutoCreate:
    def test_profile_created_on_user_save(self):
        user = User.objects.create_user(username="testuser", password="pass")
        assert UserProfile.objects.filter(user=user).exists()

    def test_profile_default_priority(self):
        user = User.objects.create_user(username="testuser2", password="pass")
        assert user.profile.priority == 100

    def test_profile_deleted_with_user(self):
        user = User.objects.create_user(username="testuser3", password="pass")
        user_id = user.pk
        user.delete()
        assert not UserProfile.objects.filter(user_id=user_id).exists()

    def test_priority_is_configurable(self):
        user = User.objects.create_user(username="editor", password="pass")
        user.profile.priority = 200
        user.profile.save()
        user.profile.refresh_from_db()
        assert user.profile.priority == 200
