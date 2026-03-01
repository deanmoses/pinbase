"""Seed Series records from data/series.json and design credits from data/credits.json.

Creates or updates Series records with names and descriptions. After OPDB/IPDB
ingest creates Person records, creates DesignCredit(series=...) records from
credits.json.

Series-Title M2M memberships are handled by ingest_titles_pinbase.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.catalog.models import DesignCredit, Person, Series

logger = logging.getLogger(__name__)

DEFAULT_SERIES_PATH = Path(__file__).parents[5] / "data" / "series.json"
DEFAULT_CREDITS_PATH = Path(__file__).parents[5] / "data" / "credits.json"


class Command(BaseCommand):
    help = "Seed Series records and series-level design credits."

    def add_arguments(self, parser):
        parser.add_argument(
            "--series",
            default=str(DEFAULT_SERIES_PATH),
            help="Path to series.json seed file.",
        )
        parser.add_argument(
            "--credits",
            default=str(DEFAULT_CREDITS_PATH),
            help="Path to credits.json seed file.",
        )

    def handle(self, *args, **options):
        series_path = options["series"]
        credits_path = options["credits"]

        with open(series_path) as f:
            series_entries = json.load(f)

        # Upsert Series records.
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

        # Seed series-level design credits.
        credits_created = credits_skipped = 0

        with open(credits_path) as f:
            credit_entries = json.load(f)

        people_by_slug = {p.slug: p for p in Person.objects.all()}

        for entry in credit_entries:
            series_slug = entry["series_slug"]
            person_slug = entry["person_slug"]
            role = entry["role"].lower()

            series_obj = series_by_slug.get(series_slug)
            if series_obj is None:
                logger.warning(
                    "Series slug %r not found — skipping credit", series_slug
                )
                credits_skipped += 1
                continue

            person_obj = people_by_slug.get(person_slug)
            if person_obj is None:
                logger.warning(
                    "Person slug %r not found (run ingest_ipdb/opdb first) — skipping",
                    person_slug,
                )
                credits_skipped += 1
                continue

            _, was_created = DesignCredit.objects.get_or_create(
                series=series_obj,
                person=person_obj,
                role=role,
            )
            if was_created:
                credits_created += 1

        self.stdout.write(
            f"  Credits: {credits_created} created, {credits_skipped} skipped"
        )
        self.stdout.write(self.style.SUCCESS("Series seed ingestion complete."))
