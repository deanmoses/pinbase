"""Seed System records from data/systems.json.

Creates or updates System records with editorial slugs, names, and
manufacturer FKs. Runs after ingest_manufacturers_pinbase so manufacturer
lookups by slug are reliable.

The mpu_strings field is used only for IPDB ingestion mapping and is
not stored on the System model.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.catalog.models import Manufacturer, System

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).parents[5] / "data" / "systems.json"


class Command(BaseCommand):
    help = "Seed System records from data/systems.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_PATH),
            help="Path to systems.json seed file.",
        )

    def handle(self, *args, **options):
        path = options["path"]
        with open(path) as f:
            entries = json.load(f)

        # Pre-fetch manufacturer lookup by slug.
        mfr_by_slug: dict[str, Manufacturer] = {
            m.slug: m for m in Manufacturer.objects.all()
        }

        created = 0
        updated = 0
        missing_mfr: list[str] = []

        for entry in entries:
            slug = entry["slug"]
            name = entry["name"]
            description = entry.get("description", "")
            mfr_slug = entry.get("manufacturer_slug")

            mfr = None
            if mfr_slug:
                mfr = mfr_by_slug.get(mfr_slug)
                if mfr is None:
                    missing_mfr.append(mfr_slug)
                    logger.warning(
                        "Manufacturer slug %r not found for system %r", mfr_slug, slug
                    )

            _, was_created = System.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "manufacturer": mfr,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(f"  Systems seed: {created} created, {updated} updated")
        if missing_mfr:
            self.stderr.write(
                f"  Warning: {len(missing_mfr)} missing manufacturer slug(s): "
                + ", ".join(sorted(set(missing_mfr)))
            )
        self.stdout.write(self.style.SUCCESS("System seed ingestion complete."))
