"""Tests for the kiosk-audience contextvar override in apps.core.licensing."""

from __future__ import annotations

from constance.test import override_config

from apps.core.licensing import (
    DISPLAY_POLICY_RANKS,
    current_audience,
    get_minimum_display_rank,
    reset_kiosk_audience,
    set_kiosk_audience,
)


class TestKioskAudienceOverride:
    """``set_kiosk_audience`` flips ``get_minimum_display_rank`` to show-all."""

    def test_default_audience_reads_constance_policy(self):
        with override_config(CONTENT_DISPLAY_POLICY="licensed-only"):
            assert current_audience() == "default"
            assert get_minimum_display_rank() == DISPLAY_POLICY_RANKS["licensed-only"]

    def test_kiosk_audience_returns_show_all_rank(self):
        token = set_kiosk_audience()
        try:
            with override_config(CONTENT_DISPLAY_POLICY="licensed-only"):
                assert current_audience() == "kiosk"
                assert get_minimum_display_rank() == DISPLAY_POLICY_RANKS["show-all"]
                assert get_minimum_display_rank() == 0
        finally:
            reset_kiosk_audience(token)

    def test_kiosk_override_ignores_constance_value(self):
        # Across every Constance choice, kiosk audience is always show-all.
        for policy in DISPLAY_POLICY_RANKS:
            token = set_kiosk_audience()
            try:
                with override_config(CONTENT_DISPLAY_POLICY=policy):
                    assert get_minimum_display_rank() == 0
            finally:
                reset_kiosk_audience(token)

    def test_reset_restores_default_audience(self):
        assert current_audience() == "default"
        token = set_kiosk_audience()
        assert current_audience() == "kiosk"
        reset_kiosk_audience(token)
        assert current_audience() == "default"

    def test_unknown_constance_value_falls_back_to_licensed_only_rank(self):
        # Documents the existing fallback in get_minimum_display_rank: an
        # unrecognised policy returns rank 38 (the licensed-only floor).
        with override_config(CONTENT_DISPLAY_POLICY="bogus-value"):
            assert get_minimum_display_rank() == 38
