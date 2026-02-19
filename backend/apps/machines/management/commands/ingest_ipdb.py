"""Ingest pinball machines from an IPDB JSON dump.

Creates PinballModel records, asserts Claims for each field, and creates
Person/DesignCredit records for design credits.
"""

from __future__ import annotations

import json
import logging

from django.core.management.base import BaseCommand

from apps.machines.ingestion.ipdb_title_fixes import TITLE_FIXES
from apps.machines.ingestion.parsers import (
    parse_credit_string,
    parse_ipdb_date,
    parse_ipdb_machine_type,
)
from apps.machines.models import Claim, DesignCredit, Person, PinballModel, Source

logger = logging.getLogger(__name__)

# IPDB field → Claim field_name for direct/extra_data claims.
CLAIM_FIELDS = {
    "Title": "name",
    "IpdbId": "ipdb_id",
    "ManufacturerId": "manufacturer",
    "Players": "player_count",
    "Theme": "theme",
    "ProductionNumber": "production_quantity",
    "MPU": "mpu",
    "AverageFunRating": "ipdb_rating",
    # Extra data (no dedicated column)
    "NotableFeatures": "notable_features",
    "Notes": "notes",
    "Toys": "toys",
    "MarketingSlogans": "marketing_slogans",
    "CommonAbbreviations": "abbreviation",
    "ModelNumber": "model_number",
}

# IPDB credit field → DesignCredit role.
CREDIT_FIELDS = {
    "DesignBy": "design",
    "ArtBy": "art",
    "DotsAnimationBy": "animation",
    "MechanicsBy": "mechanics",
    "MusicBy": "music",
    "SoundBy": "sound",
    "SoftwareBy": "software",
}


class Command(BaseCommand):
    help = "Ingest pinball machines from an IPDB JSON dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ipdb",
            default="../data/dump1/data/ipdbdatabase.json",
            help="Path to IPDB JSON dump.",
        )

    def handle(self, *args, **options):
        ipdb_path = options["ipdb"]

        source, _ = Source.objects.update_or_create(
            slug="ipdb",
            defaults={
                "name": "IPDB",
                "source_type": "database",
                "priority": 10,
                "url": "https://www.ipdb.org",
            },
        )

        with open(ipdb_path) as f:
            data = json.load(f)

        records = data["Data"]
        self.stdout.write(f"Processing {len(records)} IPDB records...")

        # Pre-load person cache for credit lookups.
        person_cache: dict[str, Person] = {
            p.name.lower(): p for p in Person.objects.all()
        }

        created = 0
        updated = 0
        failed = 0
        failed_ids = []

        for rec in records:
            try:
                stats = self._ingest_record(rec, source, person_cache)
                if stats == "created":
                    created += 1
                else:
                    updated += 1
            except Exception:
                ipdb_id = rec.get("IpdbId", "?")
                logger.exception("Failed to ingest IPDB record %s", ipdb_id)
                failed += 1
                failed_ids.append(ipdb_id)

        self.stdout.write(f"  Created: {created}, Updated: {updated}, Failed: {failed}")
        if failed_ids:
            self.stderr.write(f"  Failed IDs: {failed_ids}")

        self.stdout.write(self.style.SUCCESS("IPDB ingestion complete."))

        if failed:
            raise SystemExit(1)

    def _ingest_record(
        self,
        rec: dict,
        source: Source,
        person_cache: dict[str, Person],
    ) -> str:
        ipdb_id = rec.get("IpdbId")
        title = TITLE_FIXES.get(ipdb_id, rec.get("Title", "Unknown"))

        pm, was_created = PinballModel.objects.get_or_create(
            ipdb_id=ipdb_id,
            defaults={"name": title},
        )

        # Assert claims for mapped fields.
        for ipdb_field, claim_field in CLAIM_FIELDS.items():
            value = rec.get(ipdb_field)
            if value is None or value == "":
                continue
            # Skip ManufacturerId=0 (no manufacturer assigned).
            if ipdb_field == "ManufacturerId" and value == 0:
                continue
            # Use corrected title for name claims.
            if ipdb_field == "Title" and ipdb_id in TITLE_FIXES:
                value = TITLE_FIXES[ipdb_id]
            # Convert production number to string.
            if ipdb_field == "ProductionNumber":
                value = str(value)
            Claim.objects.assert_claim(
                model=pm,
                source=source,
                field_name=claim_field,
                value=value,
            )

        # Date fields (year + month from a single IPDB field).
        date_str = rec.get("DateOfManufacture")
        if date_str:
            year, month = parse_ipdb_date(date_str)
            if year is not None:
                Claim.objects.assert_claim(
                    model=pm, source=source, field_name="year", value=year
                )
            if month is not None:
                Claim.objects.assert_claim(
                    model=pm, source=source, field_name="month", value=month
                )

        # Machine type.
        type_short = rec.get("TypeShortName")
        type_full = rec.get("Type")
        machine_type = parse_ipdb_machine_type(type_short, type_full)
        if machine_type:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="machine_type", value=machine_type
            )

        # Image URLs → extra_data claim.
        image_files = rec.get("ImageFiles")
        if image_files:
            urls = [img["Url"] for img in image_files if img.get("Url")]
            if urls:
                Claim.objects.assert_claim(
                    model=pm, source=source, field_name="image_urls", value=urls
                )

        # Design credits (direct Person + DesignCredit creation, not claims).
        for ipdb_field, role in CREDIT_FIELDS.items():
            raw = rec.get(ipdb_field)
            if not raw:
                continue
            names = parse_credit_string(raw)
            for name in names:
                person = self._get_or_create_person(name, person_cache)
                DesignCredit.objects.get_or_create(model=pm, person=person, role=role)

        return "created" if was_created else "updated"

    def _get_or_create_person(self, name: str, cache: dict[str, Person]) -> Person:
        key = name.lower()
        if key in cache:
            return cache[key]
        person, _ = Person.objects.get_or_create(name=name)
        cache[key] = person
        return person
