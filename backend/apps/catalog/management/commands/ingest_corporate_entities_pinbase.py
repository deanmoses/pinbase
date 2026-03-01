"""Seed CorporateEntity + Address records from data/corporate_entities.json.

Creates or updates CorporateEntity records linked to their parent
Manufacturer, then asserts editorial claims for name and years_active.
Also creates Address records from optional headquarters fields.

Runs after ingest_manufacturers_pinbase (for Manufacturer records).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.catalog.models import Address, CorporateEntity, Manufacturer
from apps.catalog.resolve import resolve_corporate_entity
from apps.provenance.models import Claim, Source

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).parents[5] / "data" / "corporate_entities.json"


class Command(BaseCommand):
    help = "Seed CorporateEntity records from data/corporate_entities.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_PATH),
            help="Path to corporate_entities.json seed file.",
        )

    def handle(self, *args, **options):
        path = options["path"]
        with open(path) as f:
            entries = json.load(f)

        # Pre-fetch manufacturer lookup by slug.
        mfr_by_slug: dict[str, Manufacturer] = {
            m.slug: m for m in Manufacturer.objects.all()
        }

        source, _ = Source.objects.update_or_create(
            slug="editorial",
            defaults={
                "name": "Editorial",
                "source_type": Source.SourceType.EDITORIAL,
                "priority": 300,
            },
        )
        ct_id = ContentType.objects.get_for_model(CorporateEntity).pk
        pending_claims: list[Claim] = []
        to_resolve: list[CorporateEntity] = []

        created = 0
        updated = 0
        addresses_created = 0
        missing_mfr: list[str] = []

        for entry in entries:
            mfr_slug = entry["manufacturer_slug"]
            mfr = mfr_by_slug.get(mfr_slug)
            if mfr is None:
                missing_mfr.append(mfr_slug)
                logger.warning(
                    "Manufacturer slug %r not found for CE %r",
                    mfr_slug,
                    entry["name"],
                )
                continue

            name = entry["name"]

            # Format years_active from year_start/year_end.
            year_start = entry.get("year_start")
            year_end = entry.get("year_end")
            if year_start and year_end:
                years_active = f"{year_start}-{year_end}"
            elif year_start:
                years_active = f"{year_start}-present"
            else:
                years_active = ""

            obj, was_created = CorporateEntity.objects.update_or_create(
                manufacturer=mfr,
                name=name,
                defaults={"years_active": years_active},
            )
            if was_created:
                created += 1
            else:
                updated += 1

            pending_claims.append(
                Claim(
                    content_type_id=ct_id,
                    object_id=obj.pk,
                    field_name="name",
                    value=name,
                )
            )
            if years_active:
                pending_claims.append(
                    Claim(
                        content_type_id=ct_id,
                        object_id=obj.pk,
                        field_name="years_active",
                        value=years_active,
                    )
                )

            to_resolve.append(obj)

            # Create Address from optional headquarters fields.
            city = entry.get("headquarters_city", "")
            state = entry.get("headquarters_state", "")
            country = entry.get("headquarters_country", "")
            if city or state or country:
                _, addr_created = Address.objects.get_or_create(
                    corporate_entity=obj,
                    city=city,
                    state=state,
                    country=country,
                )
                if addr_created:
                    addresses_created += 1

        self.stdout.write(
            f"  Corporate entities seed: {created} created, {updated} updated"
        )
        if addresses_created:
            self.stdout.write(f"  Addresses: {addresses_created} created")
        if missing_mfr:
            self.stderr.write(
                f"  Warning: {len(missing_mfr)} missing manufacturer slug(s): "
                + ", ".join(sorted(set(missing_mfr)))
            )

        if pending_claims:
            stats = Claim.objects.bulk_assert_claims(source, pending_claims)
            self.stdout.write(
                f"  Claims: {stats['unchanged']} unchanged, "
                f"{stats['created']} created, {stats['superseded']} superseded"
            )
            for ce in to_resolve:
                resolve_corporate_entity(ce)

        self.stdout.write(
            self.style.SUCCESS("Corporate entity seed ingestion complete.")
        )
