"""Re-resolve all PinballModels from their claims."""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

from apps.machines.resolve import resolve_all


class Command(BaseCommand):
    help = "Re-resolve all PinballModels from their active claims."

    def handle(self, *args, **options):
        # Silence per-query SQL logging — bulk_update generates huge CASE WHEN
        # statements that produce tens of MB of debug output.
        logging.getLogger("django.db.backends").setLevel(logging.WARNING)

        self.stdout.write("Resolving claims...")
        count = resolve_all()
        from apps.machines.cache import invalidate_all

        invalidate_all()
        self.stdout.write(self.style.SUCCESS(f"Resolved {count} models."))
