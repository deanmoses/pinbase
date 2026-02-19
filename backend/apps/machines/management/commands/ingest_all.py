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

        for step in STEPS:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Running {step}..."))
            kwargs = {}
            if step == "ingest_manufacturers":
                kwargs = {"ipdb": ipdb_path, "opdb": opdb_path}
            elif step == "ingest_ipdb":
                kwargs = {"ipdb": ipdb_path}
            elif step == "ingest_opdb":
                kwargs = {"opdb": opdb_path}
            call_command(step, stdout=self.stdout, stderr=self.stderr, **kwargs)

        self.stdout.write(self.style.SUCCESS("Full ingestion pipeline complete."))
