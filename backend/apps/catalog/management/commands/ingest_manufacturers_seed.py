"""Seed manufacturer records from data/manufacturers.json.

Creates or updates Manufacturer records with editorial slugs and names.
Asserts editorial description claims at priority 300 so they win over
OPDB (200), IPDB (100), and Wikidata (75) during resolve_claims.

Runs before ingest_manufacturers so IPDB/OPDB ingest can match against
stable slugs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.catalog.models import Manufacturer
from apps.catalog.resolve import resolve_manufacturer
from apps.provenance.models import Claim, Source

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

        source, _ = Source.objects.update_or_create(
            slug="editorial",
            defaults={
                "name": "Editorial",
                "source_type": Source.SourceType.EDITORIAL,
                "priority": 300,
            },
        )
        ct_id = ContentType.objects.get_for_model(Manufacturer).pk
        pending_claims: list[Claim] = []
        to_resolve: list[Manufacturer] = []

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

            description = entry.get("description", "")
            if description:
                pending_claims.append(
                    Claim(
                        content_type_id=ct_id,
                        object_id=obj.pk,
                        field_name="description",
                        value=description,
                    )
                )
                to_resolve.append(obj)

        self.stdout.write(
            f"  Manufacturers seed: {created} created, {updated} updated, "
            f"{unchanged} unchanged"
        )

        if pending_claims:
            stats = Claim.objects.bulk_assert_claims(source, pending_claims)
            self.stdout.write(
                f"  Description claims: {stats['unchanged']} unchanged, "
                f"{stats['created']} created, {stats['superseded']} superseded"
            )
            for mfr in to_resolve:
                resolve_manufacturer(mfr)

        self.stdout.write(self.style.SUCCESS("Manufacturer seed ingestion complete."))
