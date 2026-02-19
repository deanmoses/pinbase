"""Re-resolve all PinballModels from their claims."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.machines.resolve import resolve_all


class Command(BaseCommand):
    help = "Re-resolve all PinballModels from their active claims."

    def handle(self, *args, **options):
        self.stdout.write("Resolving claims...")
        count = resolve_all()
        self.stdout.write(self.style.SUCCESS(f"Resolved {count} models."))
