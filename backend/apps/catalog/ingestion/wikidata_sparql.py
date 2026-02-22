"""Wikidata SPARQL fetch and parse utilities for pinball person data.

No Django dependency — pure Python. Testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import requests

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = (
    "Pinbase/1.0 (pinball museum project; contact via github.com/deanmoses/pinbase)"
)

# Wikidata date precision constants (wikibase:timePrecision)
PRECISION_DAY = 11
PRECISION_MONTH = 10
PRECISION_YEAR = 9
# Anything below PRECISION_YEAR (decade=8, century=7, ...) is too coarse to use.

# SPARQL query: returns one row per (person, pinball machine) pair.
# Uses psv: (property statement value) path to get date precision qualifiers.
_SPARQL_QUERY = """
SELECT DISTINCT
  ?person ?personLabel ?personDescription
  ?birthDate ?birthDatePrecision
  ?deathDate ?deathDatePrecision
  ?birthPlaceLabel ?citizenshipLabel
  ?image
  ?work ?workLabel
WHERE {
  # Pinball machine instances (Q192198 = pinball machine)
  ?work wdt:P31 wd:Q192198 .

  # Person credited on the machine: developer (P178), creator (P170), or director (P57)
  { ?work wdt:P178 ?person . }
  UNION
  { ?work wdt:P170 ?person . }
  UNION
  { ?work wdt:P57  ?person . }

  # Filter to humans only (Q5 = human)
  ?person wdt:P31 wd:Q5 .

  OPTIONAL {
    ?person wdt:P569 ?birthDate .
    ?person p:P569/psv:P569/wikibase:timePrecision ?birthDatePrecision .
  }
  OPTIONAL {
    ?person wdt:P570 ?deathDate .
    ?person p:P570/psv:P570/wikibase:timePrecision ?deathDatePrecision .
  }
  OPTIONAL {
    ?person wdt:P19 ?birthPlace .
    ?birthPlace rdfs:label ?birthPlaceLabel .
    FILTER(LANG(?birthPlaceLabel) = "en")
  }
  OPTIONAL {
    ?person wdt:P27 ?citizenship .
    ?citizenship rdfs:label ?citizenshipLabel .
    FILTER(LANG(?citizenshipLabel) = "en")
  }
  OPTIONAL { ?person wdt:P18 ?image . }

  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY ?person ?work
"""


@dataclass
class WikidataPerson:
    qid: str  # e.g. "Q312897"
    name: str
    description: str  # Short Wikidata description (1-2 sentences), may be ""
    birth_date: str | None  # Raw "+1951-10-15T00:00:00Z" or None
    birth_precision: int | None  # 9/10/11 or None
    death_date: str | None
    death_precision: int | None
    birth_place: str | None  # English label, e.g. "Chicago"
    nationality: str | None  # English label, e.g. "United States of America"
    photo_url: str | None  # https://commons.wikimedia.org/wiki/Special:FilePath/...
    work_labels: list[str] = field(default_factory=list)  # Pinball machine names
    citation_url: str = ""  # https://www.wikidata.org/wiki/{qid}


def fetch_sparql(timeout: int = 60) -> dict:
    """Fetch raw SPARQL results from Wikidata.

    Returns the raw JSON response dict (with ``results``/``bindings`` keys).
    Raises ``requests.RequestException`` on network failure.
    Raises ``ValueError`` if the response is missing expected keys.
    """
    resp = requests.get(
        SPARQL_ENDPOINT,
        params={"query": _SPARQL_QUERY, "format": "json"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if "results" not in data or "bindings" not in data["results"]:
        raise ValueError(f"Unexpected SPARQL response shape: {list(data.keys())}")
    return data


def parse_sparql_results(data: dict) -> list[WikidataPerson]:
    """Parse raw SPARQL JSON into a list of WikidataPerson.

    Groups (person, machine) rows by QID — one WikidataPerson per person.
    Returns list sorted by name for deterministic output.
    """
    persons: dict[str, WikidataPerson] = {}

    for binding in data["results"]["bindings"]:
        person_uri = binding.get("person", {}).get("value", "")
        if not person_uri:
            continue
        qid = person_uri.rstrip("/").rsplit("/", 1)[-1]  # "Q312897"

        if qid not in persons:
            persons[qid] = WikidataPerson(
                qid=qid,
                name=binding.get("personLabel", {}).get("value", ""),
                description=binding.get("personDescription", {}).get("value", ""),
                birth_date=binding.get("birthDate", {}).get("value"),
                birth_precision=_int_binding(binding, "birthDatePrecision"),
                death_date=binding.get("deathDate", {}).get("value"),
                death_precision=_int_binding(binding, "deathDatePrecision"),
                birth_place=binding.get("birthPlaceLabel", {}).get("value"),
                nationality=binding.get("citizenshipLabel", {}).get("value"),
                photo_url=_normalize_photo_url(binding.get("image", {}).get("value")),
                citation_url=f"https://www.wikidata.org/wiki/{qid}",
            )

        wp = persons[qid]

        # Accumulate work labels (deduplicated).
        work_label = binding.get("workLabel", {}).get("value", "")
        if work_label and work_label not in wp.work_labels:
            wp.work_labels.append(work_label)

    return sorted(persons.values(), key=lambda p: p.name.lower())


def parse_wikidata_date(
    date_str: str | None,
    precision: int | None,
) -> tuple[int | None, int | None, int | None]:
    """Parse a Wikidata date string into (year, month, day) integer components.

    Returns ``(None, None, None)`` if the date is absent or precision is too
    coarse (decade or broader).

    Precision rules:
    - precision < PRECISION_YEAR (decade+): ``(None, None, None)``
    - precision == PRECISION_YEAR: ``(year, None, None)``
    - precision == PRECISION_MONTH: ``(year, month, None)``
    - precision >= PRECISION_DAY or None: ``(year, month, day)``
    """
    if not date_str:
        return None, None, None

    # Wikidata dates look like "+1951-10-15T00:00:00Z" or "-0044-01-01T00:00:00Z".
    # Strip leading sign and trailing time component.
    raw = date_str.lstrip("+")
    date_part = raw.split("T")[0]  # "1951-10-15" or "-0044-01-01"

    # Handle BCE dates (negative years).
    negative = date_part.startswith("-")
    if negative:
        date_part = date_part[1:]  # strip the "-"

    parts = date_part.split("-")
    if len(parts) < 1:
        return None, None, None

    try:
        year = int(parts[0])
        if negative:
            year = -year
        month = int(parts[1]) if len(parts) > 1 else None
        day = int(parts[2]) if len(parts) > 2 else None
    except ValueError, IndexError:
        return None, None, None

    # Apply precision filter.
    if precision is not None and precision < PRECISION_YEAR:
        return None, None, None
    if precision == PRECISION_YEAR:
        return year, None, None
    if precision == PRECISION_MONTH:
        return year, month, None
    # PRECISION_DAY or precision is None: return all components.
    return year, month, day


def _int_binding(binding: dict, key: str) -> int | None:
    val = binding.get(key, {}).get("value")
    if val is None:
        return None
    try:
        return int(val)
    except ValueError, TypeError:
        return None


def _normalize_photo_url(url: str | None) -> str | None:
    if not url:
        return None
    # Upgrade http to https.
    if url.startswith("http://"):
        url = "https://" + url[7:]
    return url
