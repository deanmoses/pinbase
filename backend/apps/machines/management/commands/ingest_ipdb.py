"""Ingest pinball machines from an IPDB JSON dump.

Creates PinballModel records, asserts Claims for each field, and creates
Person/DesignCredit records for design credits.

Claims, Persons, and DesignCredits are collected during the main loop and
written in bulk after all records are processed.
"""

from __future__ import annotations

import json
import logging
from html import unescape

from django.core.management.base import BaseCommand

from apps.machines.ingestion.bulk_utils import format_names, generate_unique_slug
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

        # --- Phase 1: Ensure all PinballModels exist ---
        existing_by_ipdb: dict[int, PinballModel] = {
            pm.ipdb_id: pm for pm in PinballModel.objects.filter(ipdb_id__isnull=False)
        }
        existing_slugs: set[str] = set(
            PinballModel.objects.values_list("slug", flat=True)
        )

        new_models: list[PinballModel] = []
        record_models: list[tuple[PinballModel, dict, bool]] = []
        skipped = 0

        for rec in records:
            ipdb_id = rec.get("IpdbId")
            if not ipdb_id:
                skipped += 1
                continue

            title = unescape(TITLE_FIXES.get(ipdb_id, rec.get("Title", "Unknown")))

            pm = existing_by_ipdb.get(ipdb_id)
            if pm:
                record_models.append((pm, rec, False))
            else:
                slug = generate_unique_slug(title, existing_slugs)
                pm = PinballModel(ipdb_id=ipdb_id, name=title, slug=slug)
                new_models.append(pm)
                existing_by_ipdb[ipdb_id] = pm
                record_models.append((pm, rec, True))

        created = len(new_models)
        matched = len(record_models) - created
        if new_models:
            PinballModel.objects.bulk_create(new_models)

        self.stdout.write(
            f"  Models — Matched: {matched}, Created: {created}, Skipped: {skipped}"
        )
        if new_models:
            self.stdout.write(
                f"    New: {format_names([pm.name for pm in new_models])}"
            )

        # --- Phase 2: Collect claims and credits ---
        pending_claims: list[Claim] = []
        credit_queue: list[tuple[int, str, str]] = []
        failed = 0
        failed_ids: list = []

        for pm, rec, _was_created in record_models:
            try:
                self._collect_record_data(pm, rec, source, pending_claims, credit_queue)
            except Exception:
                ipdb_id = rec.get("IpdbId", "?")
                logger.exception("Failed to collect data for IPDB record %s", ipdb_id)
                failed += 1
                failed_ids.append(ipdb_id)

        if failed_ids:
            self.stderr.write(f"  Failed IDs: {failed_ids}")

        # --- Bulk-assert all collected claims ---
        claim_stats = Claim.objects.bulk_assert_claims(source, pending_claims)
        self.stdout.write(
            f"  Claims: {claim_stats['unchanged']} unchanged, "
            f"{claim_stats['created']} created, "
            f"{claim_stats['superseded']} superseded, "
            f"{claim_stats['duplicates_removed']} duplicates removed"
        )

        # --- Bulk-create Persons and Credits ---
        self._bulk_create_persons_and_credits(credit_queue)

        self.stdout.write(self.style.SUCCESS("IPDB ingestion complete."))

        if failed:
            raise SystemExit(1)

    def _collect_record_data(
        self,
        pm: PinballModel,
        rec: dict,
        source: Source,
        pending_claims: list[Claim],
        credit_queue: list[tuple[int, str, str]],
    ) -> None:
        """Collect claims and credits for a single IPDB record."""
        ipdb_id = rec.get("IpdbId")

        # Collect claims for mapped fields.
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
            # Decode HTML entities in string values from IPDB.
            if isinstance(value, str):
                value = unescape(value)
            pending_claims.append(
                Claim(model_id=pm.pk, field_name=claim_field, value=value)
            )

        # Date fields (year + month from a single IPDB field).
        date_str = rec.get("DateOfManufacture")
        if date_str:
            year, month = parse_ipdb_date(date_str)
            if year is not None:
                pending_claims.append(
                    Claim(model_id=pm.pk, field_name="year", value=year)
                )
            if month is not None:
                pending_claims.append(
                    Claim(model_id=pm.pk, field_name="month", value=month)
                )

        # Machine type.
        type_short = rec.get("TypeShortName")
        type_full = rec.get("Type")
        machine_type = parse_ipdb_machine_type(type_short, type_full)
        if machine_type:
            pending_claims.append(
                Claim(model_id=pm.pk, field_name="machine_type", value=machine_type)
            )

        # Image URLs → extra_data claim.
        image_files = rec.get("ImageFiles")
        if image_files:
            urls = [img["Url"] for img in image_files if img.get("Url")]
            if urls:
                pending_claims.append(
                    Claim(model_id=pm.pk, field_name="image_urls", value=urls)
                )

        # Collect design credits for bulk creation later.
        for ipdb_field, role in CREDIT_FIELDS.items():
            raw = rec.get(ipdb_field)
            if not raw:
                continue
            names = parse_credit_string(raw)
            for name in names:
                credit_queue.append((pm.pk, name, role))

    def _bulk_create_persons_and_credits(
        self, credit_queue: list[tuple[int, str, str]]
    ) -> None:
        """Bulk-create Person and DesignCredit records from the credit queue."""
        if not credit_queue:
            return

        # Discover all unique person names needed.
        existing_persons: dict[str, Person] = {
            p.name.lower(): p for p in Person.objects.all()
        }
        existing_slugs: set[str] = set(Person.objects.values_list("slug", flat=True))

        new_persons: list[Person] = []
        seen_names: set[str] = set()
        for _, name, _ in credit_queue:
            key = name.lower()
            if key not in existing_persons and key not in seen_names:
                slug = generate_unique_slug(name, existing_slugs)
                new_persons.append(Person(name=name, slug=slug))
                seen_names.add(key)

        persons_created = len(new_persons)
        if new_persons:
            Person.objects.bulk_create(new_persons)
            # Refresh to get PKs.
            existing_persons = {p.name.lower(): p for p in Person.objects.all()}

        self.stdout.write(
            f"  Persons: {len(existing_persons) - persons_created} existing, "
            f"{persons_created} created"
        )

        # Build DesignCredit objects, skipping duplicates.
        existing_credits: set[tuple[int, int, str]] = set(
            DesignCredit.objects.values_list("model_id", "person_id", "role")
        )

        new_credits: list[DesignCredit] = []
        for pm_pk, name, role in credit_queue:
            person = existing_persons[name.lower()]
            key = (pm_pk, person.pk, role)
            if key not in existing_credits:
                new_credits.append(
                    DesignCredit(model_id=pm_pk, person_id=person.pk, role=role)
                )
                existing_credits.add(key)

        credits_created = len(new_credits)
        if new_credits:
            DesignCredit.objects.bulk_create(new_credits)

        self.stdout.write(
            f"  Design credits: "
            f"{len(existing_credits) - credits_created} existing, "
            f"{credits_created} created"
        )
