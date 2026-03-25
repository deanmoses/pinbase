"""Licensing helpers for display threshold and effective license resolution."""

from __future__ import annotations

# Maps Constance CONTENT_DISPLAY_POLICY choices to minimum permissiveness_rank.
DISPLAY_POLICY_RANKS: dict[str, int] = {
    "show-all": 0,  # Everything, including Not Allowed
    "include-unknown": 5,  # Unknown (null, rank 5) + all licensed content
    "licensed-only": 38,  # Lowest CC license (CC BY-NC-ND 2.0) and above
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


# Image field names that get license metadata denormalized into extra_data.
IMAGE_FIELDS = frozenset({"opdb.images", "ipdb.image_urls", "image_urls"})


def build_source_field_license_map() -> dict[tuple[int, str], object]:
    """Prefetch all SourceFieldLicense rows into a lookup dict.

    Returns {(source_id, field_name): license_obj}.
    """
    from apps.provenance.models import SourceFieldLicense

    return {
        (sfl.source_id, sfl.field_name): sfl.license
        for sfl in SourceFieldLicense.objects.select_related("license").all()
    }


def resolve_effective_license(claim, sfl_map: dict | None = None):
    """Resolve the effective license for a claim.

    Resolution order:
    1. claim.license (per-claim override)
    2. SourceFieldLicense for (claim.source, claim.field_name)
    3. claim.source.default_license (source-wide default)
    4. None (unknown)
    """
    if claim.license_id:
        return claim.license
    if claim.source_id:
        if sfl_map is not None:
            sfl_license = sfl_map.get((claim.source_id, claim.field_name))
            if sfl_license:
                return sfl_license
        return claim.source.default_license if claim.source else None
    return None
