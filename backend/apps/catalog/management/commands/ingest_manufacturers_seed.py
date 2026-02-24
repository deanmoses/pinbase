"""Seed manufacturer records from data/manufacturers.json.

Creates or updates Manufacturer records with editorial slugs and names.
Runs before ingest_manufacturers so IPDB/OPDB ingest can match against
stable slugs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.catalog.models import Manufacturer

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).parents[5] / "data" / "manufacturers.json"


class Command(BaseCommand):
    help = "Seed Manufacturer records from data/manufacturers.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_PATH),
            help="Path to manufacturers.json seed file.",
        )

    def handle(self, *args, **options):
        path = options["path"]
        with open(path) as f:
            entries = json.load(f)

        created = 0
        updated = 0
        unchanged = 0

        for entry in entries:
            slug = entry["slug"]
            name = entry["name"]
            defaults = {"name": name}
            obj, was_created = Manufacturer.objects.update_or_create(
                slug=slug,
                defaults=defaults,
            )
            if was_created:
                created += 1
            elif obj.name != name:
                updated += 1
            else:
                unchanged += 1

        self.stdout.write(
            f"  Manufacturers seed: {created} created, {updated} updated, "
            f"{unchanged} unchanged"
        )
        self.stdout.write(self.style.SUCCESS("Manufacturer seed ingestion complete."))
