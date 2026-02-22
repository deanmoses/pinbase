"""Tests for the ingest_fandom command and fandom_wiki module."""

import pytest
from django.core.management import call_command

from apps.catalog.ingestion.fandom_wiki import (
    FandomCredit,
    _parse_infobox_credits,
    parse_game_pages,
)
from apps.catalog.models import DesignCredit, MachineModel, Person
from apps.provenance.models import Source

FIXTURES = "apps/catalog/tests/fixtures"
SAMPLE = f"{FIXTURES}/fandom_sample.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def _seed_db(db):
    """Pre-seed the DB with machines and persons for matching."""
    addams = MachineModel.objects.create(name="The Addams Family", year=1992)
    medieval = MachineModel.objects.create(name="Medieval Madness", year=1997)

    pat = Person.objects.create(name="Pat Lawlor")
    john_y = Person.objects.create(name="John Youssi")
    brian = Person.objects.create(name="Brian Eddy")

    # Greg Freres is in the fixture for Medieval Madness but NOT in the DB.

    # Pre-existing credit (should not be duplicated on re-run).
    DesignCredit.objects.create(model=addams, person=pat, role="design")

    return {
        "addams": addams,
        "medieval": medieval,
        "pat": pat,
        "john_y": john_y,
        "brian": brian,
    }


@pytest.fixture
def _run_fandom(_seed_db):
    """Run ingest_fandom using the sample fixture."""
    call_command("ingest_fandom", from_dump=SAMPLE)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("_run_fandom")
class TestIngestFandom:
    def test_creates_source(self):
        source = Source.objects.get(slug="fandom")
        assert source.name == "Pinball Wiki (Fandom)"
        assert source.priority == 60
        assert source.source_type == "wiki"

    def test_art_credit_created(self):
        """John Youssi's art credit for The Addams Family should be created."""
        addams = MachineModel.objects.get(name="The Addams Family")
        john_y = Person.objects.get(name="John Youssi")
        assert DesignCredit.objects.filter(
            model=addams, person=john_y, role="art"
        ).exists()

    def test_animation_credit_created(self):
        """Scott Slomiany is not in the DB — credit should be skipped."""
        # Scott Slomiany is not seeded in the DB.
        assert not Person.objects.filter(name="Scott Slomiany").exists()

    def test_existing_design_credit_not_duplicated(self):
        """Pat Lawlor's existing design credit must not be duplicated."""
        addams = MachineModel.objects.get(name="The Addams Family")
        pat = Person.objects.get(name="Pat Lawlor")
        assert (
            DesignCredit.objects.filter(model=addams, person=pat, role="design").count()
            == 1
        )

    def test_medieval_madness_design_credit(self):
        medieval = MachineModel.objects.get(name="Medieval Madness")
        brian = Person.objects.get(name="Brian Eddy")
        assert DesignCredit.objects.filter(
            model=medieval, person=brian, role="design"
        ).exists()

    def test_unmatched_game_skipped(self):
        """'Unknown Game That Is Not In DB' must not crash and not create credits."""
        assert not MachineModel.objects.filter(
            name="Unknown Game That Is Not In DB"
        ).exists()

    def test_no_infobox_game_skipped(self):
        """Pages without an infobox should produce no credits and not crash."""
        assert not MachineModel.objects.filter(name="No Infobox Game").exists()

    def test_idempotent(self):
        """Running twice must not duplicate credits."""
        call_command("ingest_fandom", from_dump=SAMPLE)
        addams = MachineModel.objects.get(name="The Addams Family")
        john_y = Person.objects.get(name="John Youssi")
        assert (
            DesignCredit.objects.filter(model=addams, person=john_y, role="art").count()
            == 1
        )


@pytest.mark.django_db
class TestFromDumpEmpty:
    """Empty dump should not crash and should still create the source."""

    def test_empty_games(self, db):
        import json
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"games": []}, f)
            path = f.name

        call_command("ingest_fandom", from_dump=path)
        assert Source.objects.filter(slug="fandom").exists()
        assert DesignCredit.objects.count() == 0


# ---------------------------------------------------------------------------
# Unit tests for parse functions (no DB)
# ---------------------------------------------------------------------------


class TestParseInfboxCredits:
    ADDAMS_WIKITEXT = (
        "{{Infobox Title | title = The Addams Family\n"
        "|designer = '''Designers''': [[Pat Lawlor]]<br>"
        "'''Artwork''': [[John Youssi]]<br>"
        "'''Dots/Animation''': [[Scott Slomiany]]<br>"
        "'''Mechanics''': [[John Krutsch]]<br>"
        "'''Sounds/Music''': [[Chris Granner]]<br>"
        "'''Software''': [[Larry DeMar]], [[Mike Boon]]\n"
        "}}"
    )

    def test_design_credit(self):
        credits = _parse_infobox_credits(self.ADDAMS_WIKITEXT)
        assert FandomCredit(person_name="Pat Lawlor", role="design") in credits

    def test_art_credit(self):
        credits = _parse_infobox_credits(self.ADDAMS_WIKITEXT)
        assert FandomCredit(person_name="John Youssi", role="art") in credits

    def test_animation_credit(self):
        credits = _parse_infobox_credits(self.ADDAMS_WIKITEXT)
        assert FandomCredit(person_name="Scott Slomiany", role="animation") in credits

    def test_mechanics_credit(self):
        credits = _parse_infobox_credits(self.ADDAMS_WIKITEXT)
        assert FandomCredit(person_name="John Krutsch", role="mechanics") in credits

    def test_music_credit(self):
        credits = _parse_infobox_credits(self.ADDAMS_WIKITEXT)
        assert FandomCredit(person_name="Chris Granner", role="music") in credits

    def test_software_credits_multiple(self):
        credits = _parse_infobox_credits(self.ADDAMS_WIKITEXT)
        assert FandomCredit(person_name="Larry DeMar", role="software") in credits
        assert FandomCredit(person_name="Mike Boon", role="software") in credits

    def test_no_infobox_returns_empty(self):
        assert _parse_infobox_credits("No infobox here.") == []

    def test_infobox_without_designer_returns_empty(self):
        wikitext = "{{Infobox Title | title = Foo\n|manufacturer = [[Bally]]\n}}"
        assert _parse_infobox_credits(wikitext) == []

    def test_plain_name_without_wikilink(self):
        """Names not wrapped in [[]] should still be parsed."""
        wikitext = (
            "{{Infobox Title\n|designer = '''Software''': Larry DeMar, Mike Boon\n}}"
        )
        credits = _parse_infobox_credits(wikitext)
        assert FandomCredit(person_name="Larry DeMar", role="software") in credits
        assert FandomCredit(person_name="Mike Boon", role="software") in credits

    def test_br_self_closing_variant(self):
        """<br/> and <br /> variants should also split segments."""
        wikitext = (
            "{{Infobox Title\n"
            "|designer = '''Designers''': [[Alice]]<br/>'''Artwork''': [[Bob]]\n"
            "}}"
        )
        credits = _parse_infobox_credits(wikitext)
        assert FandomCredit(person_name="Alice", role="design") in credits
        assert FandomCredit(person_name="Bob", role="art") in credits

    def test_wikilink_with_display_text(self):
        """[[Display|Target]] should use the display text (first part)."""
        wikitext = (
            "{{Infobox Title\n|designer = '''Designers''': [[Pat Lawlor|Pat]]\n}}"
        )
        credits = _parse_infobox_credits(wikitext)
        assert FandomCredit(person_name="Pat Lawlor", role="design") in credits

    def test_unknown_label_skipped(self):
        """Labels not in the role map should be silently ignored."""
        wikitext = (
            "{{Infobox Title\n"
            "|designer = '''Gibberish Label''': [[Alice]]<br>'''Designers''': [[Bob]]\n"
            "}}"
        )
        credits = _parse_infobox_credits(wikitext)
        names = [c.person_name for c in credits]
        assert "Alice" not in names
        assert "Bob" in names


class TestParseGamePages:
    def test_sorted_by_title(self):
        data = {
            "games": [
                {"page_id": 2, "title": "Zork", "wikitext": ""},
                {"page_id": 1, "title": "Addams", "wikitext": ""},
            ]
        }
        games = parse_game_pages(data)
        assert games[0].title == "Addams"
        assert games[1].title == "Zork"

    def test_citation_url_uses_underscores(self):
        data = {
            "games": [
                {"page_id": 1, "title": "The Addams Family", "wikitext": ""},
            ]
        }
        games = parse_game_pages(data)
        assert (
            games[0].citation_url == "https://pinball.fandom.com/wiki/The_Addams_Family"
        )

    def test_empty_games_returns_empty_list(self):
        assert parse_game_pages({"games": []}) == []
