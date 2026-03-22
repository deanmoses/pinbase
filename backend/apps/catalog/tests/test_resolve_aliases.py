"""Tests for _resolve_aliases() — sweep and display-casing behaviour."""

import pytest
from django.contrib.contenttypes.models import ContentType

from apps.catalog.claims import build_relationship_claim
from apps.catalog.models import Theme
from apps.catalog.models.theme import ThemeAlias
from apps.catalog.resolve._relationships import resolve_theme_aliases
from apps.provenance.models import Claim, Source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_aliases(source, theme, aliases: list[str]) -> None:
    """Assert alias claims for *theme*, mirroring ingest_pinbase._assert_alias_claims.

    Passing an empty list puts the theme in scope with no pending claims,
    which causes the sweep to delete any stale alias rows.
    """
    ct_id = ContentType.objects.get_for_model(Theme).pk
    pending = []
    for alias_str in aliases:
        lower = alias_str.lower()
        claim_key, value = build_relationship_claim(
            "theme_alias", {"alias_value": lower, "alias_display": alias_str}
        )
        pending.append(
            Claim(
                content_type_id=ct_id,
                object_id=theme.pk,
                field_name="theme_alias",
                claim_key=claim_key,
                value=value,
            )
        )
    scope = {(ct_id, theme.pk)}
    Claim.objects.bulk_assert_claims(
        source, pending, sweep_field="theme_alias", authoritative_scope=scope
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def source(db):
    return Source.objects.create(name="Pinbase", source_type="editorial", priority=300)


@pytest.fixture
def theme(db):
    return Theme.objects.create(name="Racing", slug="racing")


# ---------------------------------------------------------------------------
# Sweep tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAliasSwept:
    def test_aliases_created_on_first_run(self, source, theme):
        _assert_aliases(source, theme, ["Drag Racing", "Motorsports"])
        resolve_theme_aliases()

        values = set(
            ThemeAlias.objects.filter(theme=theme).values_list("value", flat=True)
        )
        assert values == {"Drag Racing", "Motorsports"}

    def test_stale_aliases_swept_when_list_becomes_empty(self, source, theme):
        _assert_aliases(source, theme, ["Drag Racing"])
        resolve_theme_aliases()
        assert ThemeAlias.objects.filter(theme=theme).count() == 1

        # Next ingest: alias list is empty — stale row must be deleted.
        _assert_aliases(source, theme, [])
        resolve_theme_aliases()
        assert ThemeAlias.objects.filter(theme=theme).count() == 0

    def test_removed_alias_deleted_remaining_kept(self, source, theme):
        _assert_aliases(source, theme, ["Drag Racing", "Motorsports"])
        resolve_theme_aliases()

        _assert_aliases(source, theme, ["Drag Racing"])
        resolve_theme_aliases()

        values = set(
            ThemeAlias.objects.filter(theme=theme).values_list("value", flat=True)
        )
        assert values == {"Drag Racing"}


# ---------------------------------------------------------------------------
# Display-casing tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAliasDisplayCasing:
    def test_original_case_stored(self, source, theme):
        _assert_aliases(source, theme, ["Drag Racing"])
        resolve_theme_aliases()
        assert ThemeAlias.objects.get(theme=theme).value == "Drag Racing"

    def test_case_change_updates_existing_row(self, source, theme):
        _assert_aliases(source, theme, ["Drag Racing"])
        resolve_theme_aliases()

        _assert_aliases(source, theme, ["drag racing"])
        resolve_theme_aliases()

        # Same alias (same lowercase key), different display case — row updated.
        assert ThemeAlias.objects.filter(theme=theme).count() == 1
        assert ThemeAlias.objects.get(theme=theme).value == "drag racing"

    def test_legacy_claim_without_display_falls_back_to_lowercase(self, source, theme):
        """Claims created before alias_display was added fall back to alias_value."""
        ct_id = ContentType.objects.get_for_model(Theme).pk
        # Simulate a legacy claim with no alias_display field.
        claim_key, value = build_relationship_claim(
            "theme_alias", {"alias_value": "drag racing"}
        )
        Claim.objects.bulk_assert_claims(
            source,
            [
                Claim(
                    content_type_id=ct_id,
                    object_id=theme.pk,
                    field_name="theme_alias",
                    claim_key=claim_key,
                    value=value,
                )
            ],
            sweep_field="theme_alias",
            authoritative_scope={(ct_id, theme.pk)},
        )
        resolve_theme_aliases()
        assert ThemeAlias.objects.get(theme=theme).value == "drag racing"
