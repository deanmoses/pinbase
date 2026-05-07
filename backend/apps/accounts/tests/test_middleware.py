"""Tests for LastSeenAtMiddleware."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User


@pytest.mark.django_db
class TestLastSeenAtMiddleware:
    def test_anonymous_request_no_write(self, client):
        client.get("/api/auth/me/")
        assert User.objects.filter(last_seen_at__isnull=False).count() == 0

    def test_authenticated_first_request_writes(self):
        user = User.objects.create_user(email="alice@example.com")
        assert user.last_seen_at is None

        c = Client()
        c.force_login(user)
        c.get("/api/auth/me/")

        user.refresh_from_db()
        assert user.last_seen_at is not None

    def test_authenticated_within_debounce_no_write(self):
        recent = timezone.now() - timedelta(hours=1)
        user = User.objects.create_user(email="alice@example.com")
        User.objects.filter(pk=user.pk).update(last_seen_at=recent)

        c = Client()
        c.force_login(user)
        c.get("/api/auth/me/")

        user.refresh_from_db()
        # Unchanged (allowing for microsecond tolerance from DB round-trip).
        assert user.last_seen_at is not None
        assert abs((user.last_seen_at - recent).total_seconds()) < 1

    def test_authenticated_past_debounce_writes(self):
        stale = timezone.now() - timedelta(hours=25)
        user = User.objects.create_user(email="alice@example.com")
        User.objects.filter(pk=user.pk).update(last_seen_at=stale)

        c = Client()
        c.force_login(user)
        c.get("/api/auth/me/")

        user.refresh_from_db()
        assert user.last_seen_at is not None
        assert user.last_seen_at > stale + timedelta(hours=24)
