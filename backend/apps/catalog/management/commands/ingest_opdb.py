"""Ingest pinball machines from an OPDB JSON dump.

Matches existing MachineModels by opdb_id, then creates new records.
Asserts scalar claims only — relationship-shaping claims (title, variant_of)
are owned by Pinbase-authored Markdown files.

Claims are collected during the main loop and written in bulk afterward.
"""

from __future__ import annotations

import json
from apps.catalog.ingestion.constants import DEFAULT_OPDB_PATH
import logging

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.claims import build_relationship_claim, make_authoritative_scope
from apps.catalog.ingestion.bulk_utils import (
    format_names,
    generate_unique_slug,
)
from apps.catalog.ingestion.opdb.records import OpdbRecord
from apps.catalog.ingestion.parsers import (
    map_opdb_display,
    map_opdb_type,
    parse_opdb_date,
)
from apps.catalog.ingestion.vocabulary import (
    build_cabinet_map,
    build_feature_slug_map,
    build_reward_type_map,
    build_tag_map,
)
from apps.catalog.models import GameplayFeature, MachineModel, RewardType, Tag
from apps.catalog.resolve import (
    resolve_all_gameplay_features,
    resolve_all_reward_types,
    resolve_all_tags,
)
from apps.provenance.models import Claim, Source

logger = logging.getLogger(__name__)

# OPDB features terms that match no vocabulary and should be silently skipped.
_KNOWN_OPDB_VARIANT_LABELS: frozenset[str] = frozenset(
    {
        "Limited Edition",
        "LE",
        "Special Edition",
        "SE",
        "Premium",
        "Pro",
        "Home Edition",
        "Home ROM",
        "Shaker Motor",
        "PinSound",
        "Topper",
        "Conversion kit",
        "Converted game",
        "LED",
        "LED Upgrade",
        "Colorization",
        "Color DMD",
    }
)


def _classify_opdb_features(
    features: list[str],
    feature_map: dict[str, str],
    reward_map: dict[str, str],
    tag_map: dict[str, str],
    cabinet_map: dict[str, str],
) -> tuple[list[str], list[str], list[str], str | None, bool, list[str]]:
    """Classify OPDB features array terms against vocabulary maps.

    Priority: reward types first, then gameplay features, then tags, then cabinets.
    Also detects is_conversion from "Conversion kit" / "Converted game".

    Returns (gameplay_slugs, reward_slugs, tag_slugs, cabinet_slug, is_conversion, unmatched).
    """
    gameplay_slugs: list[str] = []
    reward_slugs: list[str] = []
    tag_slugs: list[str] = []
    cabinet_slug: str | None = None
    is_conversion = False
    unmatched: list[str] = []

    seen_gameplay: set[str] = set()
    seen_reward: set[str] = set()
    seen_tag: set[str] = set()

    for term in features:
        # is_conversion detection (before skip check).
        if term in ("Conversion kit", "Converted game"):
            is_conversion = True

        lower = term.lower()

        # Reward type takes priority.
        if lower in reward_map:
            slug = reward_map[lower]
            if slug not in seen_reward:
                seen_reward.add(slug)
                reward_slugs.append(slug)
            continue

        # Then gameplay features.
        if lower in feature_map:
            slug = feature_map[lower]
            if slug not in seen_gameplay:
                seen_gameplay.add(slug)
                gameplay_slugs.append(slug)
            continue

        # Then tags.
        if lower in tag_map:
            slug = tag_map[lower]
            if slug not in seen_tag:
                seen_tag.add(slug)
                tag_slugs.append(slug)
            continue

        # Then cabinets.
        if lower in cabinet_map:
            cabinet_slug = cabinet_map[lower]
            continue

        # Skip known variant labels silently.
        if term in _KNOWN_OPDB_VARIANT_LABELS:
            continue

        unmatched.append(term)

    return (
        gameplay_slugs,
        reward_slugs,
        tag_slugs,
        cabinet_slug,
        is_conversion,
        unmatched,
    )


class Command(BaseCommand):
    help = "Ingest pinball machines from an OPDB JSON dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--opdb",
            default=DEFAULT_OPDB_PATH,
            help="Path to OPDB JSON dump.",
        )
        parser.add_argument(
            "--changelog",
            default="",
            help="Path to OPDB changelog JSON dump.",
        )

    def handle(self, *args, **options):
        opdb_path = options["opdb"]
        changelog_path = options["changelog"]

        # Build DB-driven vocabulary maps.
        feature_map = build_feature_slug_map()
        reward_map = build_reward_type_map()
        tag_map = build_tag_map()
        cabinet_map = build_cabinet_map()

        from django.contrib.contenttypes.models import ContentType

        ct_id = ContentType.objects.get_for_model(MachineModel).pk

        source, _ = Source.objects.update_or_create(
            slug="opdb",
            defaults={
                "name": "OPDB",
                "source_type": "database",
                "priority": 200,
                "url": "https://opdb.org",
            },
        )

        # --- Changelog pre-processing ---
        if changelog_path:
            self._process_changelog(changelog_path)

        # --- Load and parse machine data into typed records ---
        with open(opdb_path) as f:
            raw_data = json.load(f)

        records: list[OpdbRecord] = []
        parse_errors = 0
        for raw in raw_data:
            if "opdb_id" not in raw:
                parse_errors += 1
                logger.warning(
                    "OPDB record missing opdb_id (name=%r)",
                    raw.get("name", "<unknown>"),
                )
                continue
            try:
                records.append(OpdbRecord.from_raw(raw))
            except (KeyError, ValueError, TypeError) as e:
                parse_errors += 1
                logger.warning(
                    "Unparseable OPDB record (id=%s): %s",
                    raw.get("opdb_id", "?"),
                    e,
                )
        if parse_errors:
            raise CommandError(
                f"{parse_errors} OPDB record(s) failed to parse — aborting to prevent partial import. "
                f"Check warnings above for details."
            )

        # Physical machines + aliases — all treated as flat records.
        machines = [r for r in records if r.is_machine and r.physical_machine != 0]
        aliases = [r for r in records if r.is_alias]
        non_physical_count = sum(
            1 for r in records if r.is_machine and r.physical_machine == 0
        )
        self.stdout.write(
            f"Processing {len(machines)} OPDB machines "
            f"({non_physical_count} non-physical skipped) "
            f"+ {len(aliases)} aliases..."
        )

        # --- Pre-fetch all MachineModels into lookup dicts ---
        by_ipdb_id: dict[int, MachineModel] = {
            pm.ipdb_id: pm for pm in MachineModel.objects.filter(ipdb_id__isnull=False)
        }
        by_opdb_id: dict[str, MachineModel] = {
            pm.opdb_id: pm for pm in MachineModel.objects.filter(opdb_id__isnull=False)
        }
        existing_slugs: set[str] = set(
            MachineModel.objects.values_list("slug", flat=True)
        )

        # --- Match/create machines ---
        new_models: list[MachineModel] = []
        models_needing_opdb_update: list[MachineModel] = []
        machine_models: list[tuple[MachineModel, OpdbRecord]] = []
        matched = 0
        created = 0

        for rec in machines:
            pm = by_opdb_id.get(rec.opdb_id)

            # Fallback: match by ipdb_id (IPDB may have created the record first).
            if not pm and rec.ipdb_id:
                pm = by_ipdb_id.get(rec.ipdb_id)

            if pm:
                matched += 1
                # Set opdb_id if not already set (cross-reference backfill).
                if pm.opdb_id is None and rec.opdb_id:
                    if rec.opdb_id not in by_opdb_id:
                        pm.opdb_id = rec.opdb_id
                        by_opdb_id[rec.opdb_id] = pm
                        models_needing_opdb_update.append(pm)
                    else:
                        logger.warning(
                            "Cannot set opdb_id=%s on %r (ipdb_id=%s): "
                            "already owned by %r",
                            rec.opdb_id,
                            pm.name,
                            rec.ipdb_id,
                            by_opdb_id[rec.opdb_id].name,
                        )
                elif pm.opdb_id and pm.opdb_id != rec.opdb_id:
                    logger.warning(
                        "MachineModel %r already has opdb_id=%s, skipping %s",
                        pm.name,
                        pm.opdb_id,
                        rec.opdb_id,
                    )
            else:
                created += 1
                slug = generate_unique_slug(rec.name, existing_slugs)
                pm = MachineModel(name=rec.name, opdb_id=rec.opdb_id, slug=slug)
                new_models.append(pm)
                by_opdb_id[rec.opdb_id] = pm
                if rec.ipdb_id:
                    by_ipdb_id[rec.ipdb_id] = pm

            machine_models.append((pm, rec))

        if new_models:
            MachineModel.objects.bulk_create(new_models)
        if models_needing_opdb_update:
            MachineModel.objects.bulk_update(models_needing_opdb_update, ["opdb_id"])

        self.stdout.write(f"  Machines — Matched: {matched}, Created: {created}")
        if new_models:
            self.stdout.write(
                f"    New: {format_names([pm.name for pm in new_models])}"
            )

        # --- Match/create aliases (flat — no variant_of classification) ---
        new_alias_models: list[MachineModel] = []
        alias_linked = 0
        alias_created = 0
        alias_skipped = 0

        for rec in aliases:
            pm = by_opdb_id.get(rec.opdb_id)

            # Fallback: match by ipdb_id (pinbase may store the parent opdb_id).
            if not pm and rec.ipdb_id:
                pm = by_ipdb_id.get(rec.ipdb_id)

            if pm:
                alias_linked += 1
            else:
                # Parent must exist to create a new alias model.
                parent = by_opdb_id.get(rec.parent_opdb_id)
                if not parent:
                    logger.warning(
                        "Alias %s (%s): parent %s not found, skipping",
                        rec.opdb_id,
                        rec.name,
                        rec.parent_opdb_id,
                    )
                    alias_skipped += 1
                    continue

                alias_created += 1
                slug = generate_unique_slug(rec.name, existing_slugs)
                pm = MachineModel(name=rec.name, opdb_id=rec.opdb_id, slug=slug)
                new_alias_models.append(pm)
                by_opdb_id[rec.opdb_id] = pm

            machine_models.append((pm, rec))

        if new_alias_models:
            MachineModel.objects.bulk_create(new_alias_models)

        self.stdout.write(
            f"  Aliases — Linked: {alias_linked}, Created: {alias_created}, "
            f"Skipped: {alias_skipped}"
        )
        if new_alias_models:
            self.stdout.write(
                f"    New: {format_names([pm.name for pm in new_alias_models])}"
            )

        # --- Collect and assert scalar claims + classify features ---
        pending_claims: list[Claim] = []
        gameplay_feature_queue: list[tuple[int, list[str]]] = []
        reward_type_queue: list[tuple[int, list[str]]] = []
        tag_queue: list[tuple[int, list[str]]] = []
        unmatched_opdb_terms: list[str] = []

        for pm, rec in machine_models:
            self._collect_claims(pm, rec, ct_id, pending_claims)

            if rec.features:
                (
                    feature_slugs,
                    reward_slugs,
                    tag_slugs,
                    cabinet_slug,
                    is_conversion,
                    unmatched,
                ) = _classify_opdb_features(
                    rec.features, feature_map, reward_map, tag_map, cabinet_map
                )
                unmatched_opdb_terms.extend(unmatched)
                if feature_slugs:
                    gameplay_feature_queue.append((pm.pk, feature_slugs))
                if reward_slugs:
                    reward_type_queue.append((pm.pk, reward_slugs))
                if tag_slugs:
                    tag_queue.append((pm.pk, tag_slugs))
                if cabinet_slug:
                    pending_claims.append(
                        Claim(
                            content_type_id=ct_id,
                            object_id=pm.pk,
                            field_name="cabinet",
                            value=cabinet_slug,
                        )
                    )
                if is_conversion:
                    pending_claims.append(
                        Claim(
                            content_type_id=ct_id,
                            object_id=pm.pk,
                            field_name="is_conversion",
                            value=True,
                        )
                    )

        claim_stats = Claim.objects.bulk_assert_claims(source, pending_claims)
        self.stdout.write(
            f"  Claims: {claim_stats['unchanged']} unchanged, "
            f"{claim_stats['created']} created, "
            f"{claim_stats['superseded']} superseded, "
            f"{claim_stats['duplicates_removed']} duplicates removed"
        )

        # --- Deactivate stale claims from prior OPDB runs ---
        # OPDB no longer asserts variant_of, title, or manufacturer claims.
        # Any active claims from previous runs must be cleaned up.
        stale_count = Claim.objects.filter(
            source=source,
            field_name__in=["variant_of", "title", "manufacturer"],
            is_active=True,
        ).update(is_active=False)
        if stale_count:
            self.stdout.write(
                f"  Deactivated {stale_count} stale claims "
                f"(variant_of/title/manufacturer)"
            )

        # --- Assert gameplay feature claims ---
        all_model_ids = {pm.pk for pm, _ in machine_models}
        self._bulk_create_gameplay_features(
            gameplay_feature_queue, source, all_model_ids
        )

        # --- Assert reward type claims ---
        self._bulk_create_reward_types(reward_type_queue, source, all_model_ids)

        # --- Assert tag claims ---
        self._bulk_create_tags(tag_queue, source, all_model_ids)

        # --- Warn about unmatched features terms ---
        if unmatched_opdb_terms:
            sample = unmatched_opdb_terms[:25]
            suffix = (
                f", ... ({len(unmatched_opdb_terms)} total not in pinbase)"
                if len(unmatched_opdb_terms) > 25
                else ""
            )
            self.stdout.write(
                self.style.WARNING(
                    f"  Unmatched OPDB feature terms: {', '.join(sample)}{suffix}"
                )
            )

        # Log OPDB manufacturers not represented in pinbase.
        from apps.catalog.models import Manufacturer

        pinbase_opdb_mfr_ids = set(
            Manufacturer.objects.filter(opdb_manufacturer_id__isnull=False).values_list(
                "opdb_manufacturer_id", flat=True
            )
        )
        opdb_mfr_ids = {
            rec.manufacturer_id for rec in machines if rec.manufacturer_id is not None
        }
        missing_mfr_count = len(opdb_mfr_ids - pinbase_opdb_mfr_ids)
        if missing_mfr_count:
            self.stdout.write(
                f"  {missing_mfr_count} OPDB manufacturer(s) not in pinbase"
            )

        self.stdout.write(self.style.SUCCESS("OPDB ingestion complete."))

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
                updated = MachineModel.objects.filter(opdb_id=deleted_id)
                # Only update if the replacement isn't already taken.
                if not MachineModel.objects.filter(opdb_id=replacement_id).exists():
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
                if MachineModel.objects.filter(opdb_id=deleted_id).exists():
                    logger.info(
                        "Changelog delete %s: model exists but not deleting",
                        deleted_id,
                    )
                deletes += 1

        self.stdout.write(
            f"  Changelog: {moves} moves applied, {deletes} deletes logged"
        )

    # ------------------------------------------------------------------
    # Claim collection
    # ------------------------------------------------------------------

    def _collect_claims(
        self,
        pm: MachineModel,
        rec: OpdbRecord,
        ct_id: int,
        pending_claims: list[Claim],
    ) -> None:
        """Collect scalar claim objects for a machine or alias record."""

        def _add(field_name: str, value) -> None:
            pending_claims.append(
                Claim(
                    content_type_id=ct_id,
                    object_id=pm.pk,
                    field_name=field_name,
                    value=value,
                )
            )

        if rec.name:
            _add("name", rec.name)
        if rec.opdb_id:
            _add("opdb_id", rec.opdb_id)

        # Date.
        if rec.manufacture_date:
            year, month = parse_opdb_date(rec.manufacture_date)
            if year is not None:
                _add("year", year)
            if month is not None:
                _add("month", month)

        # Player count.
        if rec.player_count is not None:
            _add("player_count", rec.player_count)

        # Technology generation (slug-based, resolved to FK).
        technology_generation = map_opdb_type(rec.type)
        if technology_generation:
            _add("technology_generation", technology_generation)

        # Display type (slug-based, resolved to FK).
        display_type = map_opdb_display(rec.display)
        if display_type:
            _add("display_type", display_type)

        # Cabinet and gameplay_feature/reward_type/tag claims are derived from
        # rec.features in the classification pass (handle → _classify_opdb_features).
        # Store the raw features list for reference.
        if rec.features:
            _add("opdb.features", rec.features)

        for attr, claim_field in (
            ("keywords", "opdb.keywords"),
            ("description", "opdb.description"),
            ("common_name", "opdb.common_name"),
            ("images", "opdb.images"),
        ):
            value = getattr(rec, attr)
            if value:
                _add(claim_field, value)

        # Shortname becomes a relationship claim for abbreviations.
        if rec.shortname:
            claim_key, abbr_value = build_relationship_claim(
                "abbreviation", {"value": rec.shortname}
            )
            pending_claims.append(
                Claim(
                    content_type_id=ct_id,
                    object_id=pm.pk,
                    field_name="abbreviation",
                    claim_key=claim_key,
                    value=abbr_value,
                )
            )

    # ------------------------------------------------------------------
    # Relationship bulk creators (gameplay features, reward types, tags)
    # ------------------------------------------------------------------

    def _bulk_create_gameplay_features(
        self,
        gameplay_feature_queue: list[tuple[int, list[str]]],
        source,
        all_model_ids: set[int],
    ) -> None:
        """Assert gameplay feature claims and resolve into M2M rows."""
        if not gameplay_feature_queue:
            return

        from django.contrib.contenttypes.models import ContentType

        all_slugs: set[str] = set()
        for _, slugs in gameplay_feature_queue:
            all_slugs.update(slugs)

        existing_slugs = set(
            GameplayFeature.objects.filter(slug__in=all_slugs).values_list(
                "slug", flat=True
            )
        )
        missing = all_slugs - existing_slugs
        if missing:
            logger.warning(
                "Gameplay feature slugs not found in DB (skipping): %s",
                sorted(missing),
            )

        ct_machine = ContentType.objects.get_for_model(MachineModel).pk
        feature_claims: list[Claim] = []
        for pm_pk, slugs in gameplay_feature_queue:
            for slug in slugs:
                if slug not in existing_slugs:
                    continue
                claim_key, value = build_relationship_claim(
                    "gameplay_feature", {"gameplay_feature_slug": slug}
                )
                feature_claims.append(
                    Claim(
                        content_type_id=ct_machine,
                        object_id=pm_pk,
                        field_name="gameplay_feature",
                        claim_key=claim_key,
                        value=value,
                    )
                )

        auth_scope = make_authoritative_scope(MachineModel, all_model_ids)
        feature_stats = Claim.objects.bulk_assert_claims(
            source,
            feature_claims,
            sweep_field="gameplay_feature",
            authoritative_scope=auth_scope,
        )
        self.stdout.write(
            f"  Gameplay feature claims: {feature_stats['unchanged']} unchanged, "
            f"{feature_stats['created']} created, "
            f"{feature_stats['superseded']} superseded, "
            f"{feature_stats['swept']} swept"
        )
        resolve_all_gameplay_features([], model_ids=all_model_ids)

    def _bulk_create_reward_types(
        self,
        reward_type_queue: list[tuple[int, list[str]]],
        source,
        all_model_ids: set[int],
    ) -> None:
        """Assert reward type claims and resolve into M2M rows."""
        if not reward_type_queue:
            return

        from django.contrib.contenttypes.models import ContentType

        all_slugs: set[str] = set()
        for _, slugs in reward_type_queue:
            all_slugs.update(slugs)

        existing_slugs = set(
            RewardType.objects.filter(slug__in=all_slugs).values_list("slug", flat=True)
        )
        missing = all_slugs - existing_slugs
        if missing:
            logger.warning(
                "Reward type slugs not found in DB (skipping): %s",
                sorted(missing),
            )

        ct_machine = ContentType.objects.get_for_model(MachineModel).pk
        reward_type_claims: list[Claim] = []
        for pm_pk, slugs in reward_type_queue:
            for slug in slugs:
                if slug not in existing_slugs:
                    continue
                claim_key, value = build_relationship_claim(
                    "reward_type", {"reward_type_slug": slug}
                )
                reward_type_claims.append(
                    Claim(
                        content_type_id=ct_machine,
                        object_id=pm_pk,
                        field_name="reward_type",
                        claim_key=claim_key,
                        value=value,
                    )
                )

        auth_scope = make_authoritative_scope(MachineModel, all_model_ids)
        reward_type_stats = Claim.objects.bulk_assert_claims(
            source,
            reward_type_claims,
            sweep_field="reward_type",
            authoritative_scope=auth_scope,
        )
        self.stdout.write(
            f"  Reward type claims: {reward_type_stats['unchanged']} unchanged, "
            f"{reward_type_stats['created']} created, "
            f"{reward_type_stats['superseded']} superseded, "
            f"{reward_type_stats['swept']} swept"
        )
        resolve_all_reward_types([], model_ids=all_model_ids)

    def _bulk_create_tags(
        self,
        tag_queue: list[tuple[int, list[str]]],
        source,
        all_model_ids: set[int],
    ) -> None:
        """Assert tag claims and resolve into M2M rows."""
        if not tag_queue:
            return

        from django.contrib.contenttypes.models import ContentType

        all_slugs: set[str] = set()
        for _, slugs in tag_queue:
            all_slugs.update(slugs)

        existing_slugs = set(
            Tag.objects.filter(slug__in=all_slugs).values_list("slug", flat=True)
        )
        missing = all_slugs - existing_slugs
        if missing:
            logger.warning(
                "Tag slugs not found in DB (skipping): %s",
                sorted(missing),
            )

        ct_machine = ContentType.objects.get_for_model(MachineModel).pk
        tag_claims: list[Claim] = []
        for pm_pk, slugs in tag_queue:
            for slug in slugs:
                if slug not in existing_slugs:
                    continue
                claim_key, value = build_relationship_claim("tag", {"tag_slug": slug})
                tag_claims.append(
                    Claim(
                        content_type_id=ct_machine,
                        object_id=pm_pk,
                        field_name="tag",
                        claim_key=claim_key,
                        value=value,
                    )
                )

        auth_scope = make_authoritative_scope(MachineModel, all_model_ids)
        tag_stats = Claim.objects.bulk_assert_claims(
            source,
            tag_claims,
            sweep_field="tag",
            authoritative_scope=auth_scope,
        )
        self.stdout.write(
            f"  Tag claims: {tag_stats['unchanged']} unchanged, "
            f"{tag_stats['created']} created, "
            f"{tag_stats['superseded']} superseded, "
            f"{tag_stats['swept']} swept"
        )
        resolve_all_tags([], model_ids=all_model_ids)
