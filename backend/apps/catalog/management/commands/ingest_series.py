"""Seed Series records and their Title memberships from data/series.json and data/titles.json.

Creates or updates Series records, then populates the M2M relation to Title
using OPDB group IDs from titles.json. Titles not yet in the database are
skipped with a warning (run ingest_opdb first).

Designed to be idempotent: re-running updates series metadata and
re-reconciles memberships without creating duplicates.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.catalog.models import Series, Title

logger = logging.getLogger(__name__)

DEFAULT_SERIES_PATH = Path(__file__).parents[5] / "data" / "series.json"
DEFAULT_TITLES_PATH = Path(__file__).parents[5] / "data" / "titles.json"


class Command(BaseCommand):
    help = "Seed Series records and Title memberships from data/series.json and data/titles.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--series",
            default=str(DEFAULT_SERIES_PATH),
            help="Path to series.json seed file.",
        )
        parser.add_argument(
            "--titles",
            default=str(DEFAULT_TITLES_PATH),
            help="Path to titles.json seed file.",
        )

    def handle(self, *args, **options):
        series_path = options["series"]
        titles_path = options["titles"]

        with open(series_path) as f:
            series_entries = json.load(f)
        with open(titles_path) as f:
            title_entries = json.load(f)

        # Upsert series records.
        series_created = series_updated = 0
        series_by_slug: dict[str, Series] = {}

        for entry in series_entries:
            slug = entry["slug"]
            name = entry["name"]
            description = entry.get("description", "")
            obj, was_created = Series.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "description": description},
            )
            series_by_slug[slug] = obj
            if was_created:
                series_created += 1
            else:
                series_updated += 1

        self.stdout.write(
            f"  Series: {series_created} created, {series_updated} updated"
        )

        # Build a lookup of Title by opdb_id prefix.
        # Title.opdb_id stores the group ID (e.g. "G5pe4"), which is the same
        # value referenced in titles.json.
        titles_by_opdb_id = {t.opdb_id: t for t in Title.objects.exclude(opdb_id="")}

        # Reconcile M2M memberships.
        memberships_added = memberships_skipped = 0
        for entry in title_entries:
            series_slug = entry["series_slug"]
            opdb_id = entry["opdb_id"]

            series_obj = series_by_slug.get(series_slug)
            if series_obj is None:
                logger.warning("Series slug %r not found — skipping", series_slug)
                memberships_skipped += 1
                continue

            title_obj = titles_by_opdb_id.get(opdb_id)
            if title_obj is None:
                logger.warning(
                    "Title with opdb_id %r not found (run ingest_opdb first) — skipping",
                    opdb_id,
                )
                memberships_skipped += 1
                continue

            series_obj.titles.add(title_obj)
            memberships_added += 1

        self.stdout.write(
            f"  Memberships: {memberships_added} added, {memberships_skipped} skipped"
        )
        self.stdout.write(self.style.SUCCESS("Series seed ingestion complete."))
