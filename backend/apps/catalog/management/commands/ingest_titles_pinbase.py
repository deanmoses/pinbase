"""Set Title franchise FK and Series memberships from data/titles.json.

Runs after:
  - ingest_taxonomy_pinbase (for Franchise records)
  - ingest_opdb (for Title records)
  - ingest_series (for Series records)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.catalog.models import Franchise, Series, Title

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).parents[5] / "data" / "titles.json"


class Command(BaseCommand):
    help = "Set Title franchise FK and Series memberships from data/titles.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_PATH),
            help="Path to titles.json.",
        )

    def handle(self, *args, **options):
        path = options["path"]
        with open(path) as f:
            entries = json.load(f)

        # Build lookups.
        titles_by_opdb_id = {t.opdb_id: t for t in Title.objects.all()}
        franchises_by_slug = {f.slug: f for f in Franchise.objects.all()}
        series_by_slug = {s.slug: s for s in Series.objects.all()}

        franchise_set = membership_set = skipped = 0

        for entry in entries:
            opdb_group_id = entry["opdb_group_id"]

            title = titles_by_opdb_id.get(opdb_group_id)
            if title is None:
                logger.warning(
                    "Title with opdb_id %r not found — skipping", opdb_group_id
                )
                skipped += 1
                continue

            # Set franchise FK.
            franchise_slug = entry.get("franchise_slug")
            if franchise_slug:
                franchise = franchises_by_slug.get(franchise_slug)
                if franchise is None:
                    logger.warning(
                        "Franchise slug %r not found — skipping", franchise_slug
                    )
                else:
                    if title.franchise_id != franchise.pk:
                        title.franchise = franchise
                        title.save(update_fields=["franchise", "updated_at"])
                    franchise_set += 1

            # Set series membership.
            series_slug = entry.get("series_slug")
            if series_slug:
                series = series_by_slug.get(series_slug)
                if series is None:
                    logger.warning("Series slug %r not found — skipping", series_slug)
                else:
                    series.titles.add(title)
                    membership_set += 1

        self.stdout.write(
            f"  Titles: {franchise_set} franchise links, "
            f"{membership_set} series memberships, {skipped} skipped"
        )
        self.stdout.write(self.style.SUCCESS("Titles seed ingestion complete."))
