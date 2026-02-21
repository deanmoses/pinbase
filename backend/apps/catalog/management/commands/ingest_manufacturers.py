"""Ingest manufacturers from IPDB and OPDB JSON dumps.

Phase 1: Parse IPDB Manufacturer strings → create Manufacturer (brand)
          and ManufacturerEntity (corporate entity) records.
Phase 2: Match OPDB manufacturers to existing brands or create new ones.
"""

from __future__ import annotations

import json
import logging

from django.core.management.base import BaseCommand

from apps.catalog.ingestion.bulk_utils import format_names, generate_unique_slug
from apps.catalog.ingestion.constants import IPDB_SKIP_MANUFACTURER_IDS
from apps.catalog.ingestion.parsers import parse_ipdb_manufacturer_string
from apps.catalog.models import Manufacturer, ManufacturerEntity

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
            f"  Brands: {ipdb_stats['brands_existing']} existing, "
            f"{ipdb_stats['brands_created']} created"
        )
        if ipdb_stats["new_brand_names"]:
            self.stdout.write(f"    New: {format_names(ipdb_stats['new_brand_names'])}")
        self.stdout.write(
            f"  Entities: {ipdb_stats['entities_existing']} existing, "
            f"{ipdb_stats['entities_created']} created"
        )
        self.stdout.write(f"  Skipped (placeholder IDs): {ipdb_stats['skipped']}")

        self.stdout.write("Phase 2: Matching OPDB manufacturers...")
        opdb_stats = self._ingest_opdb(opdb_path)
        self.stdout.write(
            f"  Matched: {opdb_stats['matched']}, "
            f"Created: {opdb_stats['created']}, "
            f"opdb_id set: {opdb_stats['opdb_id_set']}"
        )
        if opdb_stats["new_brand_names"]:
            self.stdout.write(f"    New: {format_names(opdb_stats['new_brand_names'])}")

        self.stdout.write(self.style.SUCCESS("Manufacturer ingestion complete."))

    def _ingest_ipdb(self, path: str) -> dict[str, int]:
        with open(path) as f:
            data = json.load(f)

        # Collect unique (ManufacturerId → Manufacturer string) pairs.
        raw_mfrs: dict[int, str] = {}
        for rec in data["Data"]:
            mid = rec.get("ManufacturerId")
            if mid is not None and mid not in IPDB_SKIP_MANUFACTURER_IDS:
                if mid not in raw_mfrs:
                    raw_mfrs[mid] = rec.get("Manufacturer", "")

        skipped = sum(
            1
            for r in data["Data"]
            if r.get("ManufacturerId") in IPDB_SKIP_MANUFACTURER_IDS
        )

        # Pre-fetch existing data.
        brand_cache: dict[str, Manufacturer] = {
            m.name.lower(): m for m in Manufacturer.objects.all()
        }
        existing_brand_slugs: set[str] = set(
            Manufacturer.objects.values_list("slug", flat=True)
        )
        existing_entity_ids: set[int] = set(
            ManufacturerEntity.objects.values_list("ipdb_manufacturer_id", flat=True)
        )

        # Collect new records in memory.
        new_brands: list[Manufacturer] = []
        new_entities: list[ManufacturerEntity] = []
        entity_specs: list[tuple[int, str, str, str]] = []

        for mid, raw_string in raw_mfrs.items():
            parsed = parse_ipdb_manufacturer_string(raw_string)
            brand_name = parsed["trade_name"] or parsed["company_name"]
            if not brand_name:
                logger.warning(
                    "Empty brand name for ManufacturerId %d: %r", mid, raw_string
                )
                continue

            brand_key = brand_name.lower()
            if brand_key not in brand_cache:
                slug = generate_unique_slug(
                    parsed["trade_name"] or brand_name, existing_brand_slugs
                )
                brand = Manufacturer(
                    name=brand_name,
                    slug=slug,
                    trade_name=parsed["trade_name"],
                )
                new_brands.append(brand)
                brand_cache[brand_key] = brand

            if mid not in existing_entity_ids:
                entity_specs.append(
                    (
                        mid,
                        brand_key,
                        parsed["company_name"] or brand_name,
                        parsed["years_active"],
                    )
                )
                existing_entity_ids.add(mid)

        brands_created = len(new_brands)
        if new_brands:
            Manufacturer.objects.bulk_create(new_brands)
            brand_cache = {m.name.lower(): m for m in Manufacturer.objects.all()}

        for mid, brand_key, company_name, years_active in entity_specs:
            brand = brand_cache[brand_key]
            new_entities.append(
                ManufacturerEntity(
                    manufacturer=brand,
                    ipdb_manufacturer_id=mid,
                    name=company_name,
                    years_active=years_active,
                )
            )

        entities_created = len(new_entities)
        if new_entities:
            ManufacturerEntity.objects.bulk_create(new_entities)

        return {
            "brands_existing": len(brand_cache) - brands_created,
            "brands_created": brands_created,
            "new_brand_names": [b.name for b in new_brands],
            "entities_existing": len(existing_entity_ids) - entities_created,
            "entities_created": entities_created,
            "skipped": skipped,
        }

    def _ingest_opdb(self, path: str) -> dict[str, int]:
        with open(path) as f:
            data = json.load(f)

        opdb_mfrs: dict[int, dict] = {}
        for rec in data:
            m = rec.get("manufacturer")
            if m and m.get("manufacturer_id"):
                mid = m["manufacturer_id"]
                if mid not in opdb_mfrs:
                    opdb_mfrs[mid] = m

        name_cache: dict[str, Manufacturer] = {
            m.name.lower(): m for m in Manufacturer.objects.all()
        }
        trade_cache: dict[str, Manufacturer] = {
            m.trade_name.lower(): m for m in Manufacturer.objects.exclude(trade_name="")
        }
        existing_slugs: set[str] = set(
            Manufacturer.objects.values_list("slug", flat=True)
        )

        matched = 0
        new_brands: list[Manufacturer] = []
        brands_needing_opdb_id: list[Manufacturer] = []

        for mid, m in opdb_mfrs.items():
            opdb_name = m["name"]
            opdb_full = m.get("full_name", "")
            brand = None

            brand = name_cache.get(opdb_name.lower())
            if not brand and opdb_full:
                brand = name_cache.get(opdb_full.lower())
            if not brand:
                brand = trade_cache.get(opdb_name.lower())

            if brand:
                matched += 1
            else:
                slug = generate_unique_slug(opdb_name, existing_slugs)
                brand = Manufacturer(
                    name=opdb_name,
                    slug=slug,
                    trade_name=opdb_name,
                )
                new_brands.append(brand)
                name_cache[opdb_name.lower()] = brand

            if brand.opdb_manufacturer_id is None:
                brand.opdb_manufacturer_id = mid
                if brand.pk:
                    brands_needing_opdb_id.append(brand)
            elif brand.opdb_manufacturer_id != mid:
                logger.warning(
                    "Brand %r already has opdb_manufacturer_id=%d, skipping %d",
                    brand.name,
                    brand.opdb_manufacturer_id,
                    mid,
                )

        created = len(new_brands)
        if new_brands:
            Manufacturer.objects.bulk_create(new_brands)

        opdb_id_set = len(brands_needing_opdb_id)
        if brands_needing_opdb_id:
            Manufacturer.objects.bulk_update(
                brands_needing_opdb_id, ["opdb_manufacturer_id"]
            )

        return {
            "matched": matched,
            "created": created,
            "new_brand_names": [b.name for b in new_brands],
            "opdb_id_set": opdb_id_set,
        }
