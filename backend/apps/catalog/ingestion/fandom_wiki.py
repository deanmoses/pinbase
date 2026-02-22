"""Pinball Fandom wiki fetch and parse utilities for game credit data.

No Django dependency — pure Python. Testable in isolation.

Fetch strategy
--------------
The Pinball Fandom wiki (https://pinball.fandom.com) exposes a standard
MediaWiki API.  We use the ``generator=categorymembers`` approach to iterate
all pages in ``Category:Machines`` in batches of 50, fetching their wikitext
content in the same request.  Pagination is handled automatically via the
MediaWiki ``continue`` token.

Each game page contains an ``{{Infobox Title}}`` template whose ``designer``
field encodes all credits, e.g.::

    '''Designers''': [[Larry DeMar]], [[Pat Lawlor]]<br>
    '''Artwork''': [[John Youssi]]<br>
    '''Dots/Animation''': [[Scott Slomiany]]<br>
    '''Mechanics''': [[John Krutsch]]<br>
    '''Sounds/Music''': [[Chris Granner]]<br>
    '''Software''': Larry DeMar, [[Mike Boon]]

This provides roles (art, animation, mechanics) that Wikidata does not cover.

Dump format written by ``fetch_game_pages()`` (and read by ``--from-dump``):
``{"games": [{"page_id": int, "title": str, "wikitext": str}, ...]}``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests

FANDOM_API = "https://pinball.fandom.com/api.php"
FANDOM_WIKI_BASE = "https://pinball.fandom.com/wiki"
USER_AGENT = "Pinbase/1.0 (Project of The Flip pinball museum; contact via github.com/deanmoses/pinbase)"

# Map of bold-label text in the infobox designer field → DesignCredit.role value.
# Keys are lowercase for case-insensitive matching.
_LABEL_TO_ROLE: dict[str, str] = {
    "designers": "design",
    "designer": "design",
    "design": "design",
    "concept, design": "design",
    "artwork": "art",
    "art": "art",
    "artist": "art",
    "dots/animation": "animation",
    "animation": "animation",
    "dots": "animation",
    "mechanics": "mechanics",
    "mechanical": "mechanics",
    "sounds/music": "music",
    "music": "music",
    "sounds": "sound",
    "sound": "sound",
    "software": "software",
    "programmer": "software",
    "code": "software",
    "voice": "voice",
}

# Regex to strip wikilinks: [[display|target]] → display, [[name]] → name.
_WIKILINK_RE = re.compile(r"\[\[([^\]|]*?)(?:\|[^\]]*?)?\]\]")

# Regex to extract a credit segment: '''Label''': persons
_CREDIT_SEGMENT_RE = re.compile(r"'''([^']+)'''\s*:\s*(.*)", re.DOTALL)

# Regex to find and extract the {{Infobox Title}} template content.
# Matches from the opening {{ to its matching }}.
_INFOBOX_START_RE = re.compile(r"\{\{Infobox\s+Title\b", re.IGNORECASE)


@dataclass
class FandomCredit:
    person_name: str
    role: str  # DesignCredit.role value


@dataclass
class FandomGame:
    page_id: int
    title: str
    credits: list[FandomCredit] = field(default_factory=list)
    citation_url: str = ""


def fetch_game_pages(timeout: int = 10) -> dict:
    """Fetch all game pages from Category:Machines and return a dump dict.

    The returned dict has shape ``{"games": [{"page_id", "title", "wikitext"}, ...]}``
    — suitable for passing to ``parse_game_pages()`` or saving as a ``--dump`` file.

    Raises ``requests.RequestException`` on network failure.
    """
    params: dict = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": "Category:Machines",
        "gcmnamespace": "0",
        "gcmlimit": "50",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "*",
        "format": "json",
        "formatversion": "2",
    }

    pages: list[dict] = []

    while True:
        resp = requests.get(
            FANDOM_API,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        query = data.get("query", {})
        for page in query.get("pages", []):
            page_id = page.get("pageid")
            title = page.get("title", "")
            revisions = page.get("revisions", [])
            if not revisions:
                continue
            rev = revisions[0]
            # formatversion=2 puts content in slots.main.content
            slots = rev.get("slots", {})
            wikitext = slots.get("main", {}).get("content", rev.get("content", ""))
            if wikitext:
                pages.append({"page_id": page_id, "title": title, "wikitext": wikitext})

        if "continue" not in data:
            break
        # Advance pagination — merge all continue params into next request.
        params.update(data["continue"])

    return {"games": pages}


def parse_game_pages(data: dict) -> list[FandomGame]:
    """Parse the fetch_game_pages() dump into a list of FandomGame.

    ``data`` must have a ``"games"`` key containing a list of dicts with
    ``"page_id"``, ``"title"``, and ``"wikitext"`` keys.

    Returns a list sorted by title for deterministic output.
    Games with no parseable credits are included (empty credits list).
    """
    games: list[FandomGame] = []
    for entry in data.get("games", []):
        page_id = entry.get("page_id", 0)
        title = entry.get("title", "")
        wikitext = entry.get("wikitext", "")
        credits = _parse_infobox_credits(wikitext)
        title_slug = title.replace(" ", "_")
        games.append(
            FandomGame(
                page_id=page_id,
                title=title,
                credits=credits,
                citation_url=f"{FANDOM_WIKI_BASE}/{title_slug}",
            )
        )
    return sorted(games, key=lambda g: g.title.lower())


def _parse_infobox_credits(wikitext: str) -> list[FandomCredit]:
    """Parse credits from a game page's wikitext.

    Extracts the ``{{Infobox Title}}`` template, finds the ``designer`` field,
    and parses role-labeled segments into FandomCredit objects.

    Returns an empty list if no infobox or designer field is found.
    """
    infobox = _extract_infobox(wikitext)
    if not infobox:
        return []

    designer_value = _extract_field(infobox, "designer")
    if not designer_value:
        return []

    return _parse_designer_field(designer_value)


def _extract_infobox(wikitext: str) -> str:
    """Return the raw content between {{ and the matching }} for Infobox Title."""
    m = _INFOBOX_START_RE.search(wikitext)
    if not m:
        return ""

    start = m.start()
    depth = 0
    i = start
    while i < len(wikitext) - 1:
        if wikitext[i : i + 2] == "{{":
            depth += 1
            i += 2
        elif wikitext[i : i + 2] == "}}":
            depth -= 1
            if depth == 0:
                return wikitext[start : i + 2]
            i += 2
        else:
            i += 1
    return ""


def _extract_field(infobox: str, field_name: str) -> str:
    """Extract the value of a named field from wikitext template content.

    Handles multi-line values by reading until the next ``|`` at depth 0
    or the closing ``}}``.
    """
    pattern = re.compile(r"\|\s*" + re.escape(field_name) + r"\s*=\s*", re.IGNORECASE)
    m = pattern.search(infobox)
    if not m:
        return ""

    start = m.end()
    depth = 0
    i = start
    while i < len(infobox):
        ch = infobox[i]
        if infobox[i : i + 2] in ("{{", "[["):
            depth += 1
            i += 2
        elif infobox[i : i + 2] in ("}}", "]]"):
            depth -= 1
            if depth < 0:
                # Hit closing }} of the template itself.
                return infobox[start:i].strip()
            i += 2
        elif ch == "|" and depth == 0:
            return infobox[start:i].strip()
        else:
            i += 1
    return infobox[start:].strip()


def _parse_designer_field(value: str) -> list[FandomCredit]:
    """Parse the raw ``designer`` field value into FandomCredit objects.

    Splits on ``<br>`` variants, then for each segment matches the pattern
    ``'''Label''': person1, person2, ...`` and maps the label to a role.
    Segments without a recognisable label are skipped.
    """
    # Normalise <br> variants to a single sentinel.
    normalised = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    segments = [s.strip() for s in normalised.split("\n") if s.strip()]

    credits: list[FandomCredit] = []
    for segment in segments:
        m = _CREDIT_SEGMENT_RE.match(segment)
        if not m:
            continue
        label = m.group(1).strip()
        persons_raw = m.group(2).strip()

        role = _LABEL_TO_ROLE.get(label.lower())
        if not role:
            continue

        for name in _split_person_names(persons_raw):
            if name:
                credits.append(FandomCredit(person_name=name, role=role))

    return credits


def _split_person_names(raw: str) -> list[str]:
    """Strip wikilinks and split a comma-separated person list into names."""
    # Strip wikilinks: [[Display|Target]] → Display, [[Name]] → Name.
    stripped = _WIKILINK_RE.sub(lambda m: m.group(1), raw)
    # Strip any remaining wiki markup (bold/italic apostrophes).
    stripped = stripped.replace("'''", "").replace("''", "")
    return [name.strip() for name in stripped.split(",")]
