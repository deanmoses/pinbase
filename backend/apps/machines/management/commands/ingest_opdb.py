"""Ingest pinball machines from an OPDB JSON dump.

Matches existing PinballModels by ipdb_id cross-reference, then by opdb_id,
then creates new records. Skips alias records (is_machine != True).
"""

from __future__ import annotations

import json
import logging

from django.core.management.base import BaseCommand

from apps.machines.ingestion.parsers import (
    map_opdb_display,
    map_opdb_type,
    parse_opdb_date,
)
from apps.machines.models import Claim, PinballModel, Source

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest pinball machines from an OPDB JSON dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--opdb",
            default="../data/dump1/data/opdb-20250825.json",
            help="Path to OPDB JSON dump.",
        )

    def handle(self, *args, **options):
        opdb_path = options["opdb"]

        source, _ = Source.objects.update_or_create(
            slug="opdb",
            defaults={
                "name": "OPDB",
                "source_type": "database",
                "priority": 20,
                "url": "https://opdb.org",
            },
        )

        with open(opdb_path) as f:
            data = json.load(f)

        # Filter to machines only.
        machines = [r for r in data if r.get("is_machine") is True]
        aliases_skipped = len(data) - len(machines)
        self.stdout.write(
            f"Processing {len(machines)} OPDB machines ({aliases_skipped} aliases skipped)..."
        )

        matched = 0
        created = 0
        failed = 0
        failed_ids = []

        for rec in machines:
            try:
                result = self._ingest_record(rec, source)
                if result == "matched":
                    matched += 1
                else:
                    created += 1
            except Exception:
                opdb_id = rec.get("opdb_id", "?")
                logger.exception("Failed to ingest OPDB record %s", opdb_id)
                failed += 1
                failed_ids.append(opdb_id)

        self.stdout.write(f"  Matched: {matched}, Created: {created}, Failed: {failed}")
        if failed_ids:
            self.stderr.write(f"  Failed IDs: {failed_ids}")

        self.stdout.write(self.style.SUCCESS("OPDB ingestion complete."))

        if failed:
            raise SystemExit(1)

    def _ingest_record(self, rec: dict, source: Source) -> str:
        opdb_id = rec.get("opdb_id")
        ipdb_id = rec.get("ipdb_id")
        name = rec.get("name", "Unknown")

        # Try to match existing PinballModel.
        pm = None
        was_matched = False

        # 1. Match by ipdb_id cross-reference.
        if ipdb_id:
            pm = PinballModel.objects.filter(ipdb_id=ipdb_id).first()

        # 2. Match by opdb_id.
        if not pm and opdb_id:
            pm = PinballModel.objects.filter(opdb_id=opdb_id).first()

        if pm:
            was_matched = True
            # Set opdb_id if not already set.
            if pm.opdb_id is None and opdb_id:
                pm.opdb_id = opdb_id
                pm.save(update_fields=["opdb_id"])
            elif pm.opdb_id and opdb_id and pm.opdb_id != opdb_id:
                logger.warning(
                    "PinballModel %r already has opdb_id=%s, skipping %s",
                    pm.name,
                    pm.opdb_id,
                    opdb_id,
                )
        else:
            pm = PinballModel.objects.create(name=name, opdb_id=opdb_id)

        # Assert claims.
        if name:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="name", value=name
            )
        if opdb_id:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="opdb_id", value=opdb_id
            )

        # Manufacturer (claimed as OPDB manufacturer_id).
        mfr = rec.get("manufacturer")
        if mfr and mfr.get("manufacturer_id"):
            Claim.objects.assert_claim(
                model=pm,
                source=source,
                field_name="manufacturer",
                value=mfr["manufacturer_id"],
            )

        # Date.
        date_str = rec.get("manufacture_date")
        if date_str:
            year, month = parse_opdb_date(date_str)
            if year is not None:
                Claim.objects.assert_claim(
                    model=pm, source=source, field_name="year", value=year
                )
            if month is not None:
                Claim.objects.assert_claim(
                    model=pm, source=source, field_name="month", value=month
                )

        # Player count.
        player_count = rec.get("player_count")
        if player_count is not None:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="player_count", value=player_count
            )

        # Machine type.
        machine_type = map_opdb_type(rec.get("type"))
        if machine_type:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="machine_type", value=machine_type
            )

        # Display type.
        display_type = map_opdb_display(rec.get("display"))
        if display_type:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="display_type", value=display_type
            )

        # Extra data fields.
        features = rec.get("features")
        if features:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="features", value=features
            )

        keywords = rec.get("keywords")
        if keywords:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="keywords", value=keywords
            )

        description = rec.get("description")
        if description:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="description", value=description
            )

        return "matched" if was_matched else "created"
