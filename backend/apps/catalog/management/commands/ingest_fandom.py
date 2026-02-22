"""Ingest pinball game credit data from the Pinball Fandom wiki.

Fetches (or loads from a local dump) game pages in Category:Machines,
parses credit roles from the {{Infobox Title}} designer field, matches
games and persons to existing DB records, and creates DesignCredit rows.

Usage::

    # Live fetch (also saves a dump for inspection):
    python manage.py ingest_fandom --dump /tmp/fandom_raw.json

    # Re-run from an existing dump (skips network call):
    python manage.py ingest_fandom --from-dump /tmp/fandom_raw.json
"""

from __future__ import annotations

import json
import logging

from django.core.management.base import BaseCommand

from apps.catalog.ingestion.fandom_wiki import (
    fetch_game_pages,
    parse_game_pages,
)
from apps.catalog.models import DesignCredit, MachineModel, Person
from apps.provenance.models import Source

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest pinball game credit data from the Pinball Fandom wiki."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default="",
            metavar="PATH",
            help="Save the raw fetched JSON to this file.",
        )
        parser.add_argument(
            "--from-dump",
            default="",
            dest="from_dump",
            metavar="PATH",
            help="Load JSON from this file instead of fetching live.",
        )

    def handle(self, *args, **options):
        dump_path = options["dump"]
        from_dump = options["from_dump"]

        # 1. Fetch or load page data.
        if from_dump:
            self.stdout.write(f"Loading Fandom data from {from_dump}...")
            with open(from_dump) as f:
                raw_data = json.load(f)
        else:
            self.stdout.write("Fetching game pages from Pinball Fandom wiki...")
            raw_data = fetch_game_pages()

        # 2. Optionally save dump.
        if dump_path:
            with open(dump_path, "w") as f:
                json.dump(raw_data, f, indent=2)
            self.stdout.write(f"  Saved raw dump to {dump_path}")

        # 3. Parse into FandomGame list.
        games = parse_game_pages(raw_data)

        # 4. Upsert Fandom source.
        Source.objects.update_or_create(
            slug="fandom",
            defaults={
                "name": "Pinball Wiki (Fandom)",
                "source_type": "wiki",
                "priority": 60,
                "url": "https://pinball.fandom.com",
            },
        )

        # 5. Load existing records into lookup dicts (name → object).
        existing_machines: dict[str, MachineModel] = {
            m.name.lower(): m for m in MachineModel.objects.all()
        }
        existing_persons: dict[str, Person] = {
            p.name.lower(): p for p in Person.objects.all()
        }

        # Load existing credits as (model_id, person_id, role) set.
        existing_credits: set[tuple[int, int, str]] = set(
            DesignCredit.objects.values_list("model_id", "person_id", "role")
        )

        verbosity = options["verbosity"]

        # 6–8. Match games, persons; collect new credits.
        new_credits: list[DesignCredit] = []
        credits_by_role: dict[str, int] = {}
        # person_name → list of "role on machine" strings for the summary
        persons_credited: dict[str, list[str]] = {}
        matched_games = 0
        unmatched_games: list[str] = []
        matched_persons: set[str] = set()
        unmatched_persons: set[str] = set()
        credits_found = 0
        credits_existing = 0

        for game in games:
            machine = existing_machines.get(game.title.lower())
            if machine is None:
                unmatched_games.append(game.title)
                if verbosity >= 2:
                    self.stdout.write(f"  [NO MATCH] {game.title}")
                continue

            matched_games += 1
            if verbosity >= 2:
                self.stdout.write(f"  [MATCH]    {game.title}")

            for credit in game.credits:
                person = existing_persons.get(credit.person_name.lower())
                if person is None:
                    unmatched_persons.add(credit.person_name)
                    continue
                matched_persons.add(person.name)
                credits_found += 1
                key = (machine.pk, person.pk, credit.role)
                if key not in existing_credits:
                    new_credits.append(
                        DesignCredit(
                            model_id=machine.pk,
                            person_id=person.pk,
                            role=credit.role,
                        )
                    )
                    existing_credits.add(key)
                    credits_by_role[credit.role] = (
                        credits_by_role.get(credit.role, 0) + 1
                    )
                    persons_credited.setdefault(person.name, []).append(
                        f"{credit.role} on {machine.name}"
                    )
                else:
                    credits_existing += 1

        if new_credits:
            DesignCredit.objects.bulk_create(new_credits)

        # 9. Summary.
        b, r = "\033[1m", "\033[0m"
        dim, undim = "\033[2m", "\033[22m"
        if persons_credited:
            items = ", ".join(
                f"{name}: {', '.join(sorted(persons_credited[name]))}"
                for name in sorted(persons_credited)
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Persons with new credits ({len(persons_credited)}): "
                )
                + f"{dim}{items}{undim}"
            )
        if unmatched_persons:
            self.stdout.write(
                self.style.WARNING(f"  Unmatched persons ({len(unmatched_persons)}): ")
                + f"{dim}{', '.join(sorted(unmatched_persons))}{undim}"
            )
        if unmatched_games:
            self.stdout.write(
                self.style.WARNING(f"  Unmatched games ({len(unmatched_games)}): ")
                + f"{dim}{', '.join(sorted(unmatched_games))}{undim}"
            )
        role_breakdown = ", ".join(
            f"{role}: {n}"
            for role, n in sorted(credits_by_role.items(), key=lambda x: -x[1])
        )
        n_games = len(games)
        n_persons = len(matched_persons) + len(unmatched_persons)
        self.stdout.write(
            f"{b}  Games:  {r} {n_games} found, {matched_games} matched, {len(unmatched_games)} unmatched"
        )
        self.stdout.write(
            f"{b}  Persons:{r} {n_persons} found, {len(matched_persons)} matched, {len(unmatched_persons)} unmatched"
        )
        self.stdout.write(
            f"{b}  Credits:{r} {credits_found} found, {len(new_credits)} created, {credits_existing} existing"
            + (f" {dim}({role_breakdown}){undim}" if role_breakdown else "")
        )
        self.stdout.write(self.style.SUCCESS("Fandom ingestion complete."))
