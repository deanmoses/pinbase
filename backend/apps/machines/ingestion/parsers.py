"""Parsing utilities for IPDB and OPDB data ingestion."""

from __future__ import annotations

import re


def parse_ipdb_date(s: str | None) -> tuple[int | None, int | None]:
    """Parse IPDB datetime string like "1992-03-01T00:00:00" into (year, month).

    Returns (None, None) for empty or unparseable values.
    """
    if not s:
        return None, None
    match = re.match(r"(\d{4})-(\d{2})", s)
    if not match:
        return None, None
    year = int(match.group(1))
    month = int(match.group(2))
    # IPDB uses month=1 as a placeholder when only year is known.
    if month == 1 and s.endswith("01-01T00:00:00"):
        month = None
    return year, month


def parse_opdb_date(s: str | None) -> tuple[int | None, int | None]:
    """Parse OPDB date string like "1992-03-01" into (year, month).

    Returns (None, None) for empty or unparseable values.
    """
    if not s:
        return None, None
    match = re.match(r"(\d{4})-(\d{2})", s)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def parse_ipdb_machine_type(
    type_short: str | None, type_full: str | None = None
) -> str:
    """Map IPDB TypeShortName (and full Type fallback) to our MachineType value.

    IPDB uses "EM" and "SS" in TypeShortName. Pure Mechanical machines have an
    empty TypeShortName but Type="Pure Mechanical".
    """
    if type_short:
        mapping = {"EM": "EM", "SS": "SS"}
        result = mapping.get(type_short.strip(), "")
        if result:
            return result
    if type_full and "pure mechanical" in type_full.lower():
        return "PM"
    return ""


def parse_ipdb_manufacturer_string(raw: str | None) -> dict[str, str]:
    """Parse IPDB Manufacturer string into components.

    Example input:
        "D. Gottlieb & Company, of Chicago, Illinois (1931-1977) [Trade Name: Gottlieb]"

    Returns dict with keys: company_name, trade_name, years_active.
    All values default to empty string if not found.
    """
    if not raw:
        return {"company_name": "", "trade_name": "", "years_active": ""}

    # Extract trade name from [Trade Name: X]
    trade_match = re.search(r"\[Trade Name:\s*(.+?)\]", raw)
    trade_name = trade_match.group(1).strip() if trade_match else ""

    # Extract years from (YYYY-YYYY) or (YYYY-present) or (YYYY)
    years_match = re.search(r"\((\d{4}(?:-(?:\d{4}|present))?)\)", raw)
    years_active = years_match.group(1) if years_match else ""

    # Company name: text before ", of" or before "(" or before "["
    company = raw
    # Remove the trade name bracket
    company = re.sub(r"\s*\[Trade Name:.*?\]", "", company)
    # Remove years
    company = re.sub(r"\s*\(\d{4}.*?\)", "", company)
    # Remove location (", of ...")
    company = re.sub(r",\s*of\s+.*$", "", company)
    company = company.strip().rstrip(",")

    return {
        "company_name": company,
        "trade_name": trade_name,
        "years_active": years_active,
    }


def parse_credit_string(raw: str | None) -> list[str]:
    """Split IPDB credit string into individual person names.

    Handles comma-separated names and strips parenthetical qualifiers
    like "(aka Doane)" or "(Undisclosed)".

    Returns empty list for empty input.
    """
    if not raw:
        return []
    # Split on comma
    parts = raw.split(",")
    names = []
    for part in parts:
        # Remove parentheticals
        name = re.sub(r"\s*\(.*?\)", "", part).strip()
        if not name:
            continue
        # Skip known non-names
        if name.lower() in ("undisclosed", "unknown", "n/a", "none"):
            continue
        names.append(name)
    return names


def map_opdb_type(t: str | None) -> str:
    """Map OPDB type string to our MachineType value."""
    if not t:
        return ""
    mapping = {"em": "EM", "ss": "SS", "me": "PM"}
    return mapping.get(t.strip().lower(), "")


def map_opdb_display(d: str | None) -> str:
    """Map OPDB display string to our DisplayType value."""
    if not d:
        return ""
    mapping = {
        "reels": "reels",
        "alphanumeric": "alpha",
        "dmd": "dmd",
        "lcd": "lcd",
        "lights": "lights",
        "cga": "cga",
    }
    return mapping.get(d.strip().lower(), "")
