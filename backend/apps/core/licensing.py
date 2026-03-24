"""Licensing helpers for display threshold and effective license resolution."""

from __future__ import annotations

# Maps Constance CONTENT_DISPLAY_POLICY choices to minimum permissiveness_rank.
DISPLAY_POLICY_RANKS: dict[str, int] = {
    "show-all": 0,  # Everything, including Not Allowed
    "include-unknown": 5,  # Unknown (null, rank 5) + all licensed content
    "licensed-only": 38,  # Lowest CC license (CC BY-NC-ND 2.0) and above
    "public-domain-only": 99,  # CC0 and Public Domain only
}

# Effective rank for null (unknown) license.
UNKNOWN_LICENSE_RANK = 5


def get_minimum_display_rank() -> int:
    """Return the current minimum permissiveness_rank for displaying content."""
    from constance import config

    return DISPLAY_POLICY_RANKS.get(config.CONTENT_DISPLAY_POLICY, 38)


def effective_rank(license_obj) -> int:
    """Return the permissiveness_rank for a license, or UNKNOWN_LICENSE_RANK if null."""
    if license_obj is None:
        return UNKNOWN_LICENSE_RANK
    return license_obj.permissiveness_rank


def is_displayable(license_obj) -> bool:
    """Check if content with the given license meets the current display threshold."""
    return effective_rank(license_obj) >= get_minimum_display_rank()
