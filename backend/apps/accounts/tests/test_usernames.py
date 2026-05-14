"""Tests for the username format validator."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.usernames import validate_username_format


class TestValid:
    @pytest.mark.parametrize(
        "username",
        [
            "abc",  # min length
            "alice",
            "alice-smith",
            "bob-the-builder",
            "user123",
            "12345",
            "a-1",
            "a" * 20,  # max length
        ],
    )
    def test_accepts_valid(self, username):
        validate_username_format(username)  # does not raise


class TestRejected:
    @pytest.mark.parametrize(
        ("username", "code"),
        [
            ("", "too_short"),
            ("a", "too_short"),
            ("ab", "too_short"),
            ("a" * 21, "too_long"),
            ("a" * 100, "too_long"),
            ("Alice", "bad_charset"),
            ("alice!", "bad_charset"),
            ("alice_smith", "bad_charset"),
            ("alice.smith", "bad_charset"),
            ("alice smith", "bad_charset"),
            ("alice/smith", "bad_charset"),
            ("-alice", "leading_or_trailing_hyphen"),
            ("alice-", "leading_or_trailing_hyphen"),
            ("-alice-", "leading_or_trailing_hyphen"),
            ("alice--smith", "consecutive_hyphens"),
            ("a---b", "consecutive_hyphens"),
        ],
    )
    def test_raises_with_code(self, username, code):
        with pytest.raises(ValidationError) as exc_info:
            validate_username_format(username)
        assert exc_info.value.code == code
