"""Ingest pinball machines from an OPDB JSON dump.

Matches existing PinballModels by ipdb_id cross-reference, then by opdb_id,
then creates new records. Ingests both machines and aliases (with alias_of FK).
Optionally processes groups and changelog data.
"""

from __future__ import annotations

import json
import logging

from django.core.management.base import BaseCommand

from apps.machines.ingestion.parsers import (
    map_opdb_display,
    map_opdb_type,
    parse_opdb_date,
    parse_opdb_group_id,
)
from apps.machines.models import Claim, MachineGroup, PinballModel, Source

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest pinball machines from an OPDB JSON dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--opdb",
            default="../data/dump2/opdb_export_machines.json",
            help="Path to OPDB JSON dump.",
        )
        parser.add_argument(
            "--groups",
            default="",
            help="Path to OPDB groups JSON dump.",
        )
        parser.add_argument(
            "--changelog",
            default="",
            help="Path to OPDB changelog JSON dump.",
        )

    def handle(self, *args, **options):
        opdb_path = options["opdb"]
        groups_path = options["groups"]
        changelog_path = options["changelog"]

        source, _ = Source.objects.update_or_create(
            slug="opdb",
            defaults={
                "name": "OPDB",
                "source_type": "database",
                "priority": 20,
                "url": "https://opdb.org",
            },
        )

        # --- Changelog pre-processing ---
        if changelog_path:
            self._process_changelog(changelog_path)

        # --- Groups pre-loading ---
        groups_by_id: dict[str, dict] = {}
        if groups_path:
            groups_by_id = self._load_groups(groups_path)

        # --- Load machine data ---
        with open(opdb_path) as f:
            data = json.load(f)

        machines = [r for r in data if r.get("is_machine") is True]
        aliases = [r for r in data if r.get("is_alias") is True]
        self.stdout.write(
            f"Processing {len(machines)} OPDB machines + {len(aliases)} aliases..."
        )

        # --- Ingest machines first (aliases need parent lookup) ---
        matched = 0
        created = 0
        failed = 0
        failed_ids = []

        for rec in machines:
            try:
                result = self._ingest_record(rec, source, groups_by_id)
                if result == "matched":
                    matched += 1
                else:
                    created += 1
            except Exception:
                opdb_id = rec.get("opdb_id", "?")
                logger.exception("Failed to ingest OPDB record %s", opdb_id)
                failed += 1
                failed_ids.append(opdb_id)

        self.stdout.write(
            f"  Machines — Matched: {matched}, Created: {created}, Failed: {failed}"
        )

        # --- Ingest aliases ---
        alias_linked = 0
        alias_created = 0
        alias_skipped = 0
        alias_failed = 0

        for rec in aliases:
            try:
                result = self._ingest_alias(rec, source, groups_by_id)
                if result == "matched":
                    alias_linked += 1
                elif result == "skipped":
                    alias_skipped += 1
                else:
                    alias_created += 1
            except Exception:
                opdb_id = rec.get("opdb_id", "?")
                logger.exception("Failed to ingest OPDB alias %s", opdb_id)
                alias_failed += 1
                failed_ids.append(opdb_id)

        self.stdout.write(
            f"  Aliases — Linked: {alias_linked}, Created: {alias_created}, "
            f"Skipped: {alias_skipped}, Failed: {alias_failed}"
        )

        if failed_ids:
            self.stderr.write(f"  Failed IDs: {failed_ids}")

        self.stdout.write(self.style.SUCCESS("OPDB ingestion complete."))

        if failed or alias_failed:
            raise SystemExit(1)

    # ------------------------------------------------------------------
    # Changelog
    # ------------------------------------------------------------------

    def _process_changelog(self, path: str) -> None:
        """Apply changelog: update stale opdb_ids for 'move' actions."""
        with open(path) as f:
            entries = json.load(f)

        moves = 0
        deletes = 0
        for entry in entries:
            action = entry.get("action")
            deleted_id = entry.get("opdb_id_deleted")
            replacement_id = entry.get("opdb_id_replacement")

            if action == "move" and deleted_id and replacement_id:
                updated = PinballModel.objects.filter(opdb_id=deleted_id)
                # Only update if the replacement isn't already taken.
                if not PinballModel.objects.filter(opdb_id=replacement_id).exists():
                    count = updated.update(opdb_id=replacement_id)
                    if count:
                        self.stdout.write(
                            f"  Changelog: moved {deleted_id} → {replacement_id}"
                        )
                        moves += 1
                elif updated.exists():
                    logger.warning(
                        "Changelog move %s → %s: replacement already exists",
                        deleted_id,
                        replacement_id,
                    )
            elif action == "delete" and deleted_id:
                if PinballModel.objects.filter(opdb_id=deleted_id).exists():
                    logger.info(
                        "Changelog delete %s: model exists but not deleting",
                        deleted_id,
                    )
                deletes += 1

        self.stdout.write(
            f"  Changelog: {moves} moves applied, {deletes} deletes logged"
        )

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    def _load_groups(self, path: str) -> dict[str, dict]:
        """Load groups JSON and create/update MachineGroup records.

        Returns a dict mapping group opdb_id → group record for later lookup.
        """
        with open(path) as f:
            data = json.load(f)

        groups_by_id: dict[str, dict] = {}
        created = 0
        updated = 0

        for rec in data:
            opdb_id = rec.get("opdb_id")
            if not opdb_id:
                continue

            groups_by_id[opdb_id] = rec

            _, was_created = MachineGroup.objects.update_or_create(
                opdb_id=opdb_id,
                defaults={
                    "name": rec.get("name", ""),
                    "shortname": rec.get("shortname") or "",
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            f"  Groups: {created} created, {updated} updated "
            f"({len(groups_by_id)} total)"
        )
        return groups_by_id

    # ------------------------------------------------------------------
    # Machine ingestion
    # ------------------------------------------------------------------

    def _ingest_record(
        self, rec: dict, source: Source, groups_by_id: dict[str, dict]
    ) -> str:
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
                # Check no other model already owns this opdb_id.
                conflict = PinballModel.objects.filter(opdb_id=opdb_id).first()
                if conflict:
                    logger.warning(
                        "Cannot set opdb_id=%s on %r (ipdb_id=%s): "
                        "already owned by %r (pk=%s)",
                        opdb_id,
                        pm.name,
                        ipdb_id,
                        conflict.name,
                        conflict.pk,
                    )
                else:
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

        self._assert_claims(pm, rec, source, groups_by_id)

        return "matched" if was_matched else "created"

    # ------------------------------------------------------------------
    # Alias ingestion
    # ------------------------------------------------------------------

    def _ingest_alias(
        self, rec: dict, source: Source, groups_by_id: dict[str, dict]
    ) -> str:
        opdb_id = rec.get("opdb_id")
        ipdb_id = rec.get("ipdb_id")
        name = rec.get("name", "Unknown")

        # Find the parent machine. The alias opdb_id is G{group}-M{machine}-A{alias}.
        # The parent machine's opdb_id is G{group}-M{machine} (first two segments).
        parent_opdb_id = "-".join(opdb_id.split("-")[:2]) if opdb_id else None
        parent = (
            PinballModel.objects.filter(opdb_id=parent_opdb_id).first()
            if parent_opdb_id
            else None
        )

        if not parent:
            logger.warning(
                "Alias %s (%s): parent %s not found, skipping",
                opdb_id,
                name,
                parent_opdb_id,
            )
            return "skipped"

        # Try to match existing PinballModel (IPDB may have created it).
        pm = None
        was_matched = False

        if ipdb_id:
            pm = PinballModel.objects.filter(ipdb_id=ipdb_id).first()

        if not pm and opdb_id:
            pm = PinballModel.objects.filter(opdb_id=opdb_id).first()

        if pm:
            was_matched = True
            # Set opdb_id if not already set.
            if pm.opdb_id is None and opdb_id:
                conflict = PinballModel.objects.filter(opdb_id=opdb_id).first()
                if not conflict:
                    pm.opdb_id = opdb_id
            # Link to parent.
            if pm.alias_of_id != parent.pk:
                pm.alias_of = parent
            pm.save()
        else:
            pm = PinballModel.objects.create(
                name=name, opdb_id=opdb_id, alias_of=parent
            )

        self._assert_claims(pm, rec, source, groups_by_id)

        return "matched" if was_matched else "created"

    # ------------------------------------------------------------------
    # Shared claim logic
    # ------------------------------------------------------------------

    def _assert_claims(
        self,
        pm: PinballModel,
        rec: dict,
        source: Source,
        groups_by_id: dict[str, dict],
    ) -> None:
        """Assert all claims for a machine or alias record."""
        opdb_id = rec.get("opdb_id")
        name = rec.get("name")

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

        # --- New fields ---

        common_name = rec.get("common_name")
        if common_name:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="common_name", value=common_name
            )

        shortname = rec.get("shortname")
        if shortname:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="shortname", value=shortname
            )

        images = rec.get("images")
        if images:
            Claim.objects.assert_claim(
                model=pm, source=source, field_name="images", value=images
            )

        # Group claim (derived from opdb_id prefix).
        if opdb_id and groups_by_id:
            group_opdb_id = parse_opdb_group_id(opdb_id)
            if group_opdb_id and group_opdb_id in groups_by_id:
                Claim.objects.assert_claim(
                    model=pm,
                    source=source,
                    field_name="group",
                    value=group_opdb_id,
                )
