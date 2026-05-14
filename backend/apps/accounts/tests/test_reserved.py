"""Tests for the reserved-username policy."""

from __future__ import annotations

import pytest

from apps.accounts.reserved import is_reserved, normalize


class TestNormalize:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            # Plain lowercasing.
            ("Admin", "admin"),
            # Homoglyph fold (interior digits are letter-substitutes).
            ("M0derator", "moderator"),
            ("FlipC0mmons", "flipcommons"),
            ("L1ghtning", "llghtning"),
            # Mixed attack: interior homoglyph plus trailing pad.
            # Trailing `1` strips as padding; interior `0` folds to `o`.
            ("flipc0mmons1", "flipcommons"),
            ("9m0derator", "moderator"),  # leading pad + interior fold
            # Non-letter symbol strip.
            ("flip-commons", "flipcommons"),
            ("the_museum", "themuseum"),
            # Leading/trailing digit runs are padding, not homoglyphs —
            # stripped wholesale so `admin99` and `flip2024` collapse to
            # the reserved root rather than getting partially folded.
            ("admin2024", "admin"),
            ("flip2024", "flip"),
            ("museum1999", "museum"),
            ("99999alice", "alice"),
            ("2024flip", "flip"),
            ("admin0", "admin"),  # trailing 0 is padding, not a homoglyph
            ("0admin", "admin"),  # leading 0 is padding, not a homoglyph
            # All-digit input has no letter root; everything strips.
            ("123", ""),
            ("00", ""),
        ],
    )
    def test_normalize(self, raw, expected):
        assert normalize(raw) == expected


RESERVED = [
    # Exact matches (stem or affix).
    "admin",
    "Admin",
    "moderator",
    "flipcommons",
    "flip-commons",  # hyphen folds to stem `flipcommons`
    "the-flip",  # → `theflip` stem
    "the-museum",  # → `themuseum` stem
    "flipcommons-help",  # stem+affix across a hyphen
    # Homoglyph folds.
    "m0derator",
    "FlipC0mmons",
    # Mixed: homoglyph fold AND digit padding in one candidate.
    "flipc0mmons1",
    "9m0derator",
    "0admin2024",  # both edges padded, no interior digits
    # stem+affix and affix+stem.
    "flipadmin",
    "adminflip",
    "supportmuseum",
    # Digit padding — anti-impersonation. Leading/trailing digit
    # runs strip wholesale before the homoglyph fold runs, so a 0
    # at the edge is treated as padding (not as the letter `o`).
    "admin2024",
    "museum1999",
    "flip2024",
    "99999admin",
    "admin0",  # trailing 0 strips as padding
]


ALLOWED = [
    # `staff2024team` is affix+affix, which the matcher doesn't check
    # (would over-block e.g. `staffhelp`). Even with clean digit stripping
    # the residue `staffteam` is not a designed reserved combination.
    "staff2024team",
    # Equality, not substring.
    "flipperjones",
    "museum-springfield",
    "springfield-museum",
    "administration-fan",
    # Plausible normal handles.
    "alice",
    "bob-the-builder",
    # Affix-as-prefix of a real word — must NOT be blocked. These
    # normalize to longer strings that just happen to start with an
    # affix; the matcher requires equality, not a prefix match.
    "helper",
    "teamwork",
    "administration",
    "modular",
    "supporter",
    # Stem-as-prefix of a real word.
    "museumgoer",
    "flip-flop",
    # Digit padding around a non-reserved root must not be blocked.
    "alice99",
    "42bob",
]


class TestIsReserved:
    @pytest.mark.parametrize("candidate", RESERVED)
    def test_reserved_is_blocked(self, candidate):
        assert is_reserved(candidate) is True

    @pytest.mark.parametrize("candidate", ALLOWED)
    def test_allowed_is_not_blocked(self, candidate):
        assert is_reserved(candidate) is False
