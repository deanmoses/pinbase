"""Tests for `apps.core.rate_limits._client_ip`.

The critical regression test is the default-off case: if a deploy ever
rolls ``RATE_LIMIT_TRUST_PROXY_HEADERS`` back to its default, proxy
headers must be ignored so attacker-supplied values can't bypass
IP-keyed limiters by spraying distinct bucket keys.
"""

from __future__ import annotations

import pytest
from django.http import HttpRequest
from django.test import RequestFactory
from pytest_django.fixtures import SettingsWrapper

from apps.core.rate_limits import _client_ip


def _request(rf: RequestFactory, **meta: str) -> HttpRequest:
    req = rf.get("/")
    req.META.update(meta)
    return req


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


class TestTrustDisabled:
    """Default posture: proxy headers are noise; bucket keys off REMOTE_ADDR."""

    @pytest.fixture(autouse=True)
    def _disable_trust(self, settings: SettingsWrapper) -> None:
        settings.RATE_LIMIT_TRUST_PROXY_HEADERS = False

    def test_real_ip_header_is_ignored(self, rf: RequestFactory) -> None:
        req = _request(rf, HTTP_X_REAL_IP="9.9.9.9", REMOTE_ADDR="127.0.0.1")
        assert _client_ip(req) == "127.0.0.1"

    def test_forwarded_for_header_is_ignored(self, rf: RequestFactory) -> None:
        req = _request(
            rf,
            HTTP_X_FORWARDED_FOR="9.9.9.9, 8.8.8.8",
            REMOTE_ADDR="127.0.0.1",
        )
        assert _client_ip(req) == "127.0.0.1"

    def test_both_headers_ignored_in_favor_of_remote_addr(
        self, rf: RequestFactory
    ) -> None:
        req = _request(
            rf,
            HTTP_X_REAL_IP="9.9.9.9",
            HTTP_X_FORWARDED_FOR="1.2.3.4",
            REMOTE_ADDR="127.0.0.1",
        )
        assert _client_ip(req) == "127.0.0.1"

    def test_remote_addr_missing_falls_back_to_zero(self, rf: RequestFactory) -> None:
        req = rf.get("/")
        req.META.pop("REMOTE_ADDR", None)
        assert _client_ip(req) == "unknown"


class TestTrustEnabled:
    """Production posture: X-Real-IP is trusted; XFF is still ignored."""

    @pytest.fixture(autouse=True)
    def _enable_trust(self, settings: SettingsWrapper) -> None:
        settings.RATE_LIMIT_TRUST_PROXY_HEADERS = True

    def test_real_ip_is_used(self, rf: RequestFactory) -> None:
        req = _request(rf, HTTP_X_REAL_IP="203.0.113.7", REMOTE_ADDR="127.0.0.1")
        assert _client_ip(req) == "203.0.113.7"

    def test_forwarded_for_is_still_ignored(self, rf: RequestFactory) -> None:
        # Asserts the parsing-bug class is gone: even with trust enabled,
        # XFF is never read, so attacker-supplied left-most entries can't
        # influence the bucket key.
        req = _request(
            rf,
            HTTP_X_FORWARDED_FOR="9.9.9.9, 8.8.8.8",
            REMOTE_ADDR="127.0.0.1",
        )
        assert _client_ip(req) == "127.0.0.1"

    def test_real_ip_preferred_over_forwarded_for(self, rf: RequestFactory) -> None:
        req = _request(
            rf,
            HTTP_X_REAL_IP="203.0.113.7",
            HTTP_X_FORWARDED_FOR="9.9.9.9",
            REMOTE_ADDR="127.0.0.1",
        )
        assert _client_ip(req) == "203.0.113.7"

    def test_empty_real_ip_falls_back_to_remote_addr(self, rf: RequestFactory) -> None:
        req = _request(rf, HTTP_X_REAL_IP="   ", REMOTE_ADDR="127.0.0.1")
        assert _client_ip(req) == "127.0.0.1"

    def test_missing_real_ip_falls_back_to_remote_addr(
        self, rf: RequestFactory
    ) -> None:
        req = _request(rf, REMOTE_ADDR="127.0.0.1")
        assert _client_ip(req) == "127.0.0.1"
