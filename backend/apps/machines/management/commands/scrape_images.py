"""Scrape images for pinball machines that don't have artwork.

Quick-and-dirty tool for demo purposes — NOT for production use.

Tries three strategies in order:
1. Copy from a group sibling (same franchise, different edition)
2. Scrape IPDB page (for machines with IPDB IDs)
3. Search Bing Images (fallback for everything else)

Processes in batches with a pause between each for inspection.

Usage:
    python manage.py scrape_images                    # all machines, batches of 10
    python manage.py scrape_images --year-min 2024    # only 2024+
    python manage.py scrape_images --batch-size 5     # smaller batches
    python manage.py scrape_images --dry-run           # preview without saving
"""

from __future__ import annotations

import logging
import re
import time
from html import unescape
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from apps.machines.models import Claim, PinballModel, Source
from apps.machines.resolve import resolve_model

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Seconds to wait between network requests (be polite).
REQUEST_DELAY = 1.5


def _has_images(extra_data: dict) -> bool:
    """Check if extra_data already contains usable image URLs."""
    if extra_data.get("image_urls"):
        return True
    images = extra_data.get("images")
    if images and isinstance(images, list):
        return True
    return False


def _try_group_sibling(pm: PinballModel) -> list[str] | None:
    """Copy image URLs from a sibling in the same group."""
    if not pm.group:
        return None
    for sib in pm.group.machines.exclude(pk=pm.pk):
        ed = sib.extra_data or {}

        # Try OPDB structured images — extract best URLs.
        images = ed.get("images")
        if images and isinstance(images, list):
            urls = []
            for img in images:
                if not isinstance(img, dict):
                    continue
                img_urls = img.get("urls", {})
                url = (
                    img_urls.get("large")
                    or img_urls.get("medium")
                    or img_urls.get("small")
                )
                if url:
                    urls.append(url)
            if urls:
                return urls

        # Try IPDB flat URL list.
        ipdb_urls = ed.get("image_urls")
        if ipdb_urls and isinstance(ipdb_urls, list):
            return list(ipdb_urls)

    return None


def _try_ipdb_scrape(ipdb_id: int) -> list[str] | None:
    """Scrape image URLs from an IPDB machine page."""
    url = f"https://www.ipdb.org/machine.cgi?id={ipdb_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("IPDB request failed for id=%s: %s", ipdb_id, e)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []

    # IPDB thumbnails: /images/{id}/tn_image-{n}.png
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if f"/images/{ipdb_id}/" in src:
            full_url = urljoin("https://www.ipdb.org/", src)
            urls.append(full_url)

    return urls if urls else None


def _try_bing_images(query: str) -> list[str] | None:
    """Search Bing Images and return the first few result URLs."""
    search_url = f"https://www.bing.com/images/search?q={quote_plus(query)}&first=1"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Bing search failed for %r: %s", query, e)
        return None

    # Bing HTML-encodes quotes in data attributes; decode before parsing.
    text = unescape(resp.text)

    # Extract original image URLs from 'murl' fields in Bing's JSON metadata.
    urls = re.findall(r'"murl":"(https?://[^"]+)"', text)

    # Filter for actual image file URLs.
    image_exts = (".jpg", ".jpeg", ".png", ".webp")
    good_urls = [u for u in urls if any(u.lower().endswith(ext) for ext in image_exts)]

    # If strict extension filtering is too aggressive, fall back to all murl hits.
    if not good_urls:
        good_urls = [u for u in urls if "." in u.split("/")[-1]]

    return good_urls[:3] if good_urls else None


class Command(BaseCommand):
    help = "Scrape images for machines without artwork (demo tool)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Number of machines to process per batch (default: 10).",
        )
        parser.add_argument(
            "--year-min",
            type=int,
            default=None,
            help="Only process machines from this year onward.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be scraped without saving.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        year_min = options["year_min"]
        dry_run = options["dry_run"]

        source, _ = Source.objects.update_or_create(
            slug="web-scrape",
            defaults={
                "name": "Web Scrape",
                "source_type": "other",
                "priority": 5,
                "url": "",
                "description": "Temporary web-scraped images for demo purposes.",
            },
        )

        # Find machines without images, newest first.
        qs = PinballModel.objects.filter(alias_of__isnull=True).order_by(
            "-year", "name"
        )
        if year_min:
            qs = qs.filter(year__gte=year_min)

        machines = [pm for pm in qs if not _has_images(pm.extra_data or {})]

        total = len(machines)
        if total == 0:
            self.stdout.write(self.style.SUCCESS("All machines already have images!"))
            return

        total_batches = (total + batch_size - 1) // batch_size
        self.stdout.write(
            f"Found {total} machines without images ({total_batches} batches).\n"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing will be saved.\n"))

        for i in range(0, total, batch_size):
            batch = machines[i : i + batch_size]
            batch_num = i // batch_size + 1

            self.stdout.write(f"--- Batch {batch_num}/{total_batches} ---")

            found_count = 0
            for pm in batch:
                strategy, urls = self._find_images(pm)

                if urls:
                    found_count += 1
                    if not dry_run:
                        Claim.objects.assert_claim(
                            model=pm,
                            source=source,
                            field_name="image_urls",
                            value=urls,
                        )
                        resolve_model(pm)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  \u2713 {pm.name} [{pm.year}] \u2014 {strategy} ({len(urls)} URLs)"
                        )
                    )
                    for url in urls[:2]:
                        self.stdout.write(f"    {url}")
                    if len(urls) > 2:
                        self.stdout.write(f"    ... and {len(urls) - 2} more")
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  \u2717 {pm.name} [{pm.year}] \u2014 no images found"
                        )
                    )

            self.stdout.write(
                f"\n  Batch result: {found_count}/{len(batch)} machines got images."
            )

            # Pause between batches for inspection.
            if i + batch_size < total:
                if not dry_run:
                    self.stdout.write("\nInspect results at http://localhost:5173")
                try:
                    input("Press Enter for next batch (Ctrl+C to stop)... ")
                except KeyboardInterrupt, EOFError:
                    self.stdout.write("\n\nStopped.")
                    return

        action = "would be updated" if dry_run else "updated"
        self.stdout.write(self.style.SUCCESS(f"\nDone! Machines {action}."))

    def _find_images(self, pm: PinballModel) -> tuple[str | None, list[str] | None]:
        """Try each strategy in order, return (strategy_name, urls) or (None, None)."""

        # Strategy 1: Group sibling (no network needed).
        urls = _try_group_sibling(pm)
        if urls:
            return "group sibling", urls

        # Strategy 2: IPDB scrape.
        if pm.ipdb_id:
            time.sleep(REQUEST_DELAY)
            urls = _try_ipdb_scrape(pm.ipdb_id)
            if urls:
                return "IPDB", urls

        # Strategy 3: Bing Images.
        time.sleep(REQUEST_DELAY)
        year_part = f" {pm.year}" if pm.year else ""
        query = f'"{pm.name}" pinball{year_part}'
        urls = _try_bing_images(query)
        if urls:
            return "Bing Images", urls

        return None, None
