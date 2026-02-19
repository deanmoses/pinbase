"""Ingest manufacturers from IPDB and OPDB JSON dumps.

Phase 1: Parse IPDB Manufacturer strings → create Manufacturer (brand)
          and ManufacturerEntity (corporate entity) records.
Phase 2: Match OPDB manufacturers to existing brands or create new ones.
"""

from __future__ import annotations

import json
import logging

from django.core.management.base import BaseCommand

from apps.machines.ingestion.parsers import parse_ipdb_manufacturer_string
from apps.machines.models import Manufacturer, ManufacturerEntity

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest manufacturers from IPDB and OPDB JSON dumps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ipdb",
            default="../data/dump1/data/ipdbdatabase.json",
            help="Path to IPDB JSON dump.",
        )
        parser.add_argument(
            "--opdb",
            default="../data/dump1/data/opdb-20250825.json",
            help="Path to OPDB JSON dump.",
        )

    def handle(self, *args, **options):
        ipdb_path = options["ipdb"]
        opdb_path = options["opdb"]

        self.stdout.write("Phase 1: Ingesting IPDB manufacturers...")
        ipdb_stats = self._ingest_ipdb(ipdb_path)
        self.stdout.write(
            f"  Brands created/matched: {ipdb_stats['brands']}, "
            f"Entities created: {ipdb_stats['entities']}, "
            f"Skipped (id=0): {ipdb_stats['skipped']}"
        )

        self.stdout.write("Phase 2: Matching OPDB manufacturers...")
        opdb_stats = self._ingest_opdb(opdb_path)
        self.stdout.write(
            f"  Matched: {opdb_stats['matched']}, "
            f"Created: {opdb_stats['created']}, "
            f"Unmatched: {opdb_stats['unmatched']}"
        )

        self.stdout.write(self.style.SUCCESS("Manufacturer ingestion complete."))

    def _ingest_ipdb(self, path: str) -> dict[str, int]:
        with open(path) as f:
            data = json.load(f)

        # Collect unique (ManufacturerId → Manufacturer string) pairs.
        raw_mfrs: dict[int, str] = {}
        for rec in data["Data"]:
            mid = rec.get("ManufacturerId")
            if mid is not None and mid != 0:
                if mid not in raw_mfrs:
                    raw_mfrs[mid] = rec.get("Manufacturer", "")

        skipped = sum(1 for r in data["Data"] if r.get("ManufacturerId") == 0)

        # Cache existing brands by lowercase name for dedup.
        brand_cache: dict[str, Manufacturer] = {
            m.name.lower(): m for m in Manufacturer.objects.all()
        }

        brands_touched = set()
        entities_created = 0

        for mid, raw_string in raw_mfrs.items():
            parsed = parse_ipdb_manufacturer_string(raw_string)
            brand_name = parsed["trade_name"] or parsed["company_name"]
            if not brand_name:
                logger.warning(
                    "Empty brand name for ManufacturerId %d: %r", mid, raw_string
                )
                continue

            # Get or create the brand.
            brand_key = brand_name.lower()
            if brand_key in brand_cache:
                brand = brand_cache[brand_key]
            else:
                brand, _ = Manufacturer.objects.get_or_create(
                    name=brand_name,
                    defaults={"trade_name": parsed["trade_name"]},
                )
                brand_cache[brand_key] = brand
            brands_touched.add(brand.pk)

            # Create the corporate entity.
            _, created = ManufacturerEntity.objects.get_or_create(
                ipdb_manufacturer_id=mid,
                defaults={
                    "manufacturer": brand,
                    "name": parsed["company_name"] or brand_name,
                    "years_active": parsed["years_active"],
                },
            )
            if created:
                entities_created += 1

        return {
            "brands": len(brands_touched),
            "entities": entities_created,
            "skipped": skipped,
        }

    def _ingest_opdb(self, path: str) -> dict[str, int]:
        with open(path) as f:
            data = json.load(f)

        # Collect unique OPDB manufacturers.
        opdb_mfrs: dict[int, dict] = {}
        for rec in data:
            m = rec.get("manufacturer")
            if m and m.get("manufacturer_id"):
                mid = m["manufacturer_id"]
                if mid not in opdb_mfrs:
                    opdb_mfrs[mid] = m

        # Build name lookup caches (case-insensitive).
        name_cache: dict[str, Manufacturer] = {
            m.name.lower(): m for m in Manufacturer.objects.all()
        }
        trade_cache: dict[str, Manufacturer] = {
            m.trade_name.lower(): m for m in Manufacturer.objects.exclude(trade_name="")
        }

        matched = 0
        created = 0
        unmatched_names = []

        for mid, m in opdb_mfrs.items():
            opdb_name = m["name"]
            opdb_full = m.get("full_name", "")
            brand = None

            # 1. Exact match on OPDB name
            brand = name_cache.get(opdb_name.lower())

            # 2. Exact match on OPDB full_name
            if not brand and opdb_full:
                brand = name_cache.get(opdb_full.lower())

            # 3. Trade name match
            if not brand:
                brand = trade_cache.get(opdb_name.lower())

            if brand:
                matched += 1
            else:
                brand = Manufacturer.objects.create(
                    name=opdb_name,
                    trade_name=opdb_name,
                )
                name_cache[opdb_name.lower()] = brand
                created += 1
                unmatched_names.append(opdb_name)
                logger.info("Created new brand for OPDB manufacturer: %s", opdb_name)

            # Set opdb_manufacturer_id if not already set.
            if brand.opdb_manufacturer_id is None:
                brand.opdb_manufacturer_id = mid
                brand.save(update_fields=["opdb_manufacturer_id"])
            elif brand.opdb_manufacturer_id != mid:
                logger.warning(
                    "Brand %r already has opdb_manufacturer_id=%d, skipping %d",
                    brand.name,
                    brand.opdb_manufacturer_id,
                    mid,
                )

        if unmatched_names:
            self.stdout.write(f"  New brands from OPDB: {', '.join(unmatched_names)}")

        return {
            "matched": matched,
            "created": created,
            "unmatched": len(unmatched_names),
        }
