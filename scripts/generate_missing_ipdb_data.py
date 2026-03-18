#!/usr/bin/env python3
"""Generate pinbase markdown files for IPDB data missing from the catalog.

Reads the missing_* views from data/explore2/explore2.duckdb and writes
markdown files for manufacturers, corporate entities, titles, and models
that don't yet exist in data/pinbase/.

All name parsing and manufacturer resolution live in the DuckDB views
(02_staging.sql, 04_compare.sql).  This script just reads them, slugifies,
and writes markdown.

Usage:
    python scripts/generate_missing_ipdb_data.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

import duckdb  # noqa: E402
import yaml  # noqa: E402
from django.utils.text import slugify  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "explore2" / "explore2.duckdb"
PINBASE_DIR = REPO_ROOT / "data" / "pinbase"
MFR_DIR = PINBASE_DIR / "manufacturers"
CE_DIR = PINBASE_DIR / "corporate_entities"
TITLE_DIR = PINBASE_DIR / "titles"
MODEL_DIR = PINBASE_DIR / "models"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_md(path: Path, frontmatter: dict, *, dry_run: bool = False) -> bool:
    """Write a markdown file with YAML frontmatter. Returns True if created."""
    cleaned = {k: v for k, v in frontmatter.items() if v is not None and v != "" and v != []}
    body = yaml.dump(cleaned, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)
    content = f"---\n{body}---\n"

    if path.exists() and path.read_text() == content:
        return False
    if not dry_run:
        path.write_text(content)
    return True


def _collect_existing_slugs(directory: Path) -> set[str]:
    """Collect slugs (file stems) from existing markdown files."""
    return {f.stem for f in directory.glob("*.md")}


def _unique_slug(name: str, existing: set[str]) -> str:
    """Generate a unique slug, adding to existing set to prevent collisions."""
    base = slugify(name) or "item"
    slug = base
    counter = 2
    while slug in existing:
        slug = f"{base}-{counter}"
        counter += 1
    existing.add(slug)
    return slug


def _load_frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter from a markdown file."""
    text = path.read_text()
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm = yaml.safe_load(text[3:end])
    return fm if isinstance(fm, dict) else None


# ---------------------------------------------------------------------------
# Phase 1: Manufacturers
# ---------------------------------------------------------------------------


def generate_manufacturers(con: duckdb.DuckDBPyConnection, *, dry_run: bool) -> dict[str, str]:
    """Create missing manufacturer markdown files.

    Returns {manufacturer_name (lower): slug} for all manufacturers
    (both existing and newly created).
    """
    existing_slugs = _collect_existing_slugs(MFR_DIR)

    # Build name→slug lookup from existing manufacturers.
    name_to_slug: dict[str, str] = {}
    for f in MFR_DIR.glob("*.md"):
        fm = _load_frontmatter(f)
        if fm:
            name_to_slug[fm["name"].lower()] = fm["slug"]

    # Get manufacturer names for missing CEs.
    rows = con.execute("""
        SELECT DISTINCT ice.manufacturer_name
        FROM missing_corporate_entities_ipdb mce
        JOIN ipdb_corporate_entities ice
            ON ice.ipdb_manufacturer_id = mce.ipdb_manufacturer_id
        WHERE ice.manufacturer_slug IS NULL
        ORDER BY ice.manufacturer_name
    """).fetchall()

    created = 0
    for (mfr_name,) in rows:
        if mfr_name.lower() in name_to_slug:
            continue

        slug = _unique_slug(mfr_name, existing_slugs)
        fm = {"slug": slug, "name": mfr_name}
        path = MFR_DIR / f"{slug}.md"
        if _write_md(path, fm, dry_run=dry_run):
            created += 1
            print(f"  + manufacturer: {mfr_name} ({slug})")
        name_to_slug[mfr_name.lower()] = slug

    print(f"Phase 1: Manufacturers — {created} created")
    return name_to_slug


# ---------------------------------------------------------------------------
# Phase 2: Corporate Entities
# ---------------------------------------------------------------------------


def generate_corporate_entities(
    con: duckdb.DuckDBPyConnection,
    mfr_name_to_slug: dict[str, str],
    *,
    dry_run: bool,
) -> dict[int, str]:
    """Create missing corporate entity markdown files.

    Returns {ipdb_manufacturer_id: ce_slug} for all CEs with IPDB IDs
    (both existing and newly created).
    """
    existing_slugs = _collect_existing_slugs(CE_DIR)

    # Build ipdb_manufacturer_id→slug from existing CE files on disk.
    existing_by_ipdb_id: dict[int, str] = {}
    for f in CE_DIR.glob("*.md"):
        fm = _load_frontmatter(f)
        if fm and fm.get("ipdb_manufacturer_id") is not None:
            existing_by_ipdb_id[int(fm["ipdb_manufacturer_id"])] = fm["slug"]

    rows = con.execute("""
        SELECT
            mce.ipdb_manufacturer_id,
            ice.company_name,
            ice.manufacturer_name,
            ice.manufacturer_slug,
            ice.headquarters_city,
            ice.headquarters_state,
            ice.headquarters_country
        FROM missing_corporate_entities_ipdb mce
        JOIN ipdb_corporate_entities ice
            ON ice.ipdb_manufacturer_id = mce.ipdb_manufacturer_id
        ORDER BY ice.company_name
    """).fetchall()

    ipdb_id_to_ce_slug: dict[int, str] = {}
    created = 0

    for ipdb_id, company_name, mfr_name, mfr_slug, city, state, country in rows:
        # Skip if a CE with this IPDB ID already exists on disk.
        if ipdb_id in existing_by_ipdb_id:
            ipdb_id_to_ce_slug[ipdb_id] = existing_by_ipdb_id[ipdb_id]
            continue
        ce_slug = _unique_slug(company_name, existing_slugs)

        # Resolve manufacturer slug: use DuckDB's resolution if available,
        # otherwise look up in our name→slug map (includes newly created).
        if not mfr_slug:
            mfr_slug = mfr_name_to_slug.get(mfr_name.lower())

        fm: dict[str, object] = {
            "slug": ce_slug,
            "name": company_name,
            "manufacturer_slug": mfr_slug,
            "ipdb_manufacturer_id": ipdb_id,
        }
        if city:
            fm["headquarters_city"] = city
        if state:
            fm["headquarters_state"] = state
        if country:
            fm["headquarters_country"] = country

        path = CE_DIR / f"{ce_slug}.md"
        if _write_md(path, fm, dry_run=dry_run):
            created += 1
            print(f"  + corporate entity: {company_name} ({ce_slug})")
        ipdb_id_to_ce_slug[ipdb_id] = ce_slug

    print(f"Phase 2: Corporate entities — {created} created")
    return ipdb_id_to_ce_slug


# ---------------------------------------------------------------------------
# Phase 3: Titles
# ---------------------------------------------------------------------------


def generate_titles(
    con: duckdb.DuckDBPyConnection,
    *,
    dry_run: bool,
) -> dict[str, str]:
    """Create missing title markdown files.

    Returns {title_name (lower): title_slug} for all titles relevant to
    missing models (both existing and newly created).
    """
    existing_slugs = _collect_existing_slugs(TITLE_DIR)

    rows = con.execute("""
        SELECT DISTINCT Title FROM missing_models_ipdb ORDER BY Title
    """).fetchall()

    # Build lookup for titles that already exist (by slug match).
    name_to_slug: dict[str, str] = {}
    created = 0

    for (title_name,) in rows:
        candidate_slug = slugify(title_name)
        if candidate_slug in existing_slugs:
            name_to_slug[title_name.lower()] = candidate_slug
            continue

        slug = _unique_slug(title_name, existing_slugs)
        fm = {"slug": slug, "name": title_name}
        path = TITLE_DIR / f"{slug}.md"
        if _write_md(path, fm, dry_run=dry_run):
            created += 1
            print(f"  + title: {title_name} ({slug})")
        name_to_slug[title_name.lower()] = slug

    print(f"Phase 3: Titles — {created} created")
    return name_to_slug


# ---------------------------------------------------------------------------
# Phase 4: Models
# ---------------------------------------------------------------------------


def generate_models(
    con: duckdb.DuckDBPyConnection,
    ipdb_id_to_ce_slug: dict[int, str],
    title_name_to_slug: dict[str, str],
    *,
    dry_run: bool,
) -> int:
    """Create missing model markdown files. Returns count created."""
    existing_slugs = _collect_existing_slugs(MODEL_DIR)

    # Build ipdb_id→slug from existing model files on disk.
    existing_by_ipdb_id: set[int] = set()
    for f in MODEL_DIR.glob("*.md"):
        fm = _load_frontmatter(f)
        if fm and fm.get("ipdb_id") is not None:
            existing_by_ipdb_id.add(int(fm["ipdb_id"]))

    # Also load existing CE mappings from disk for manufacturers that already
    # existed before this run.
    existing_ce_by_ipdb_id: dict[int, str] = {}
    for f in CE_DIR.glob("*.md"):
        fm = _load_frontmatter(f)
        if fm and fm.get("ipdb_manufacturer_id") is not None:
            existing_ce_by_ipdb_id[int(fm["ipdb_manufacturer_id"])] = fm["slug"]

    rows = con.execute("""
        SELECT
            IpdbId,
            Title,
            ipdb_manufacturer_id,
            ipdb_year,
            ipdb_players,
            technology_generation_slug,
            system_slug
        FROM missing_models_ipdb
        ORDER BY IpdbId
    """).fetchall()

    created = 0

    for ipdb_id, title, mfr_id, year, players, tech_gen, system in rows:
        if ipdb_id in existing_by_ipdb_id:
            continue
        slug = _unique_slug(title, existing_slugs)
        title_slug = title_name_to_slug.get(title.lower())

        ce_slug = ipdb_id_to_ce_slug.get(mfr_id) or existing_ce_by_ipdb_id.get(mfr_id)

        fm: dict[str, object] = {
            "slug": slug,
            "name": title,
            "title_slug": title_slug,
            "ipdb_id": ipdb_id,
            "corporate_entity_slug": ce_slug,
        }
        if year is not None:
            fm["year"] = year
        if players is not None:
            fm["player_count"] = players
        if tech_gen:
            fm["technology_generation_slug"] = tech_gen
        if system:
            fm["system_slug"] = system

        path = MODEL_DIR / f"{slug}.md"
        if _write_md(path, fm, dry_run=dry_run):
            created += 1
            print(f"  + model: {title} (ipdb:{ipdb_id}, {slug})")

    print(f"Phase 4: Models — {created} created")
    return created


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Parse and count but write nothing")
    args = parser.parse_args()

    con = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        mfr_name_to_slug = generate_manufacturers(con, dry_run=args.dry_run)
        ipdb_id_to_ce_slug = generate_corporate_entities(con, mfr_name_to_slug, dry_run=args.dry_run)
        title_name_to_slug = generate_titles(con, dry_run=args.dry_run)
        generate_models(con, ipdb_id_to_ce_slug, title_name_to_slug, dry_run=args.dry_run)
    finally:
        con.close()

    if args.dry_run:
        print("\n(dry run — no files written)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
