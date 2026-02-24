"""Seed MachineTypeProfile records from data/machine_types.json.

Creates or updates MachineTypeProfile records with editorial slugs, titles,
display order, and descriptions for each pinball machine era.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.catalog.models import MachineTypeProfile

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).parents[5] / "data" / "machine_types.json"


class Command(BaseCommand):
    help = "Seed MachineTypeProfile records from data/machine_types.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_PATH),
            help="Path to machine_types.json seed file.",
        )

    def handle(self, *args, **options):
        path = options["path"]
        with open(path) as f:
            entries = json.load(f)

        created = 0
        updated = 0
        unchanged = 0

        for entry in entries:
            machine_type = entry["machine_type"]
            defaults = {
                "slug": entry["slug"],
                "title": entry["title"],
                "display_order": entry["display_order"],
                "description": entry.get("description", ""),
            }
            obj, was_created = MachineTypeProfile.objects.update_or_create(
                machine_type=machine_type,
                defaults=defaults,
            )
            if was_created:
                created += 1
            elif any(getattr(obj, k) != v for k, v in defaults.items()):
                updated += 1
            else:
                unchanged += 1

        self.stdout.write(
            f"  Machine types seed: {created} created, {updated} updated, "
            f"{unchanged} unchanged"
        )
        self.stdout.write(self.style.SUCCESS("Machine type seed ingestion complete."))
