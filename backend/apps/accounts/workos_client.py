"""WorkOS client factory — centralised so tests can mock one import."""

from __future__ import annotations

from django.conf import settings
from workos import WorkOSClient


def get_workos_client() -> WorkOSClient:
    return WorkOSClient(
        api_key=settings.WORKOS_API_KEY,
        client_id=settings.WORKOS_CLIENT_ID,
    )
