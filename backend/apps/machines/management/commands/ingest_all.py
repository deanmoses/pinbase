"""Orchestrate the full ingestion pipeline.

Runs: ingest_manufacturers → ingest_ipdb → ingest_opdb → resolve_claims.
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


STEPS = [
    "ingest_manufacturers",
    "ingest_ipdb",
    "ingest_opdb",
    "resolve_claims",
]


class Command(BaseCommand):
    help = "Run the full ingestion pipeline: manufacturers, IPDB, OPDB, resolve."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ipdb",
            default="../data/dump1/ipdbdatabase.json",
            help="Path to IPDB JSON dump.",
        )
        parser.add_argument(
            "--opdb",
            default="../data/dump1/opdb_export_machines.json",
            help="Path to OPDB JSON dump.",
        )
        parser.add_argument(
            "--opdb-groups",
            default="../data/dump1/opdb_export_groups.json",
            help="Path to OPDB groups JSON dump.",
        )
        parser.add_argument(
            "--opdb-changelog",
            default="../data/dump1/opdb_changelog.json",
            help="Path to OPDB changelog JSON dump.",
        )

    def handle(self, *args, **options):
        ipdb_path = options["ipdb"]
        opdb_path = options["opdb"]
        opdb_groups = options["opdb_groups"]
        opdb_changelog = options["opdb_changelog"]

        from apps.machines.cache import invalidate_all

        try:
            for step in STEPS:
                self.stdout.write(self.style.MIGRATE_HEADING(f"Running {step}..."))
                kwargs = {}
                if step == "ingest_manufacturers":
                    kwargs = {"ipdb": ipdb_path, "opdb": opdb_path}
                elif step == "ingest_ipdb":
                    kwargs = {"ipdb": ipdb_path}
                elif step == "ingest_opdb":
                    kwargs = {
                        "opdb": opdb_path,
                        "groups": opdb_groups,
                        "changelog": opdb_changelog,
                    }
                call_command(step, stdout=self.stdout, stderr=self.stderr, **kwargs)
        finally:
            invalidate_all()

        self.stdout.write(self.style.SUCCESS("Full ingestion pipeline complete."))
