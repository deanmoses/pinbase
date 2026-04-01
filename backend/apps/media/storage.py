"""Storage key generation and helpers for the media app.

Storage keys are derived at runtime from asset UUID + rendition type.
Nothing about storage paths is stored in the database.
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import storages

from apps.media.constants import STORAGE_PREFIX
from apps.media.models import MediaRendition

logger = logging.getLogger(__name__)

_VALID_RENDITION_TYPES = {v.value for v in MediaRendition.RenditionType}

# Fixed filenames for generated renditions (always WebP).
_RENDITION_FILENAMES: dict[str, str] = {
    "thumb": "thumb.webp",
    "display": "display.webp",
}


def build_storage_key(
    asset_uuid: UUID,
    rendition_type: str,
    stored_filename: str,
) -> str:
    """Derive the storage key for a rendition.

    ``stored_filename`` is only used for the ``original`` rendition type
    (the filename stem + actual output extension after any format
    conversion).  For ``thumb``/``display`` it is ignored.
    """
    if rendition_type not in _VALID_RENDITION_TYPES:
        msg = f"Invalid rendition_type: {rendition_type!r}"
        raise ValueError(msg)

    if rendition_type == "original":
        if not stored_filename:
            msg = "stored_filename is required for original rendition"
            raise ValueError(msg)
        if " " in stored_filename or "\t" in stored_filename:
            msg = f"stored_filename must not contain whitespace: {stored_filename!r}"
            raise ValueError(msg)
        if "/" in stored_filename or "\\" in stored_filename:
            msg = (
                f"stored_filename must not contain path separator: {stored_filename!r}"
            )
            raise ValueError(msg)
        segment = f"original/{stored_filename}"
    else:
        segment = _RENDITION_FILENAMES[rendition_type]

    return f"{STORAGE_PREFIX}/{asset_uuid}/{segment}"


def build_public_url(storage_key: str) -> str:
    """Build a public URL for a storage key."""
    base = settings.MEDIA_PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/{storage_key}"


def get_media_storage():
    """Return the configured default storage backend."""
    return storages["default"]


def upload_to_storage(storage_key: str, data: bytes, content_type: str) -> None:
    """Write bytes to storage at the given key.

    Verifies the storage backend used the exact key we requested.
    S3Boto3Storage can silently rename keys when ``file_overwrite=False``
    (its default) and a collision occurs.  With UUID-based keys this is
    near-impossible, but we check anyway to prevent silent mismatches
    between the DB and storage.
    """
    storage = get_media_storage()
    file = ContentFile(data, name=storage_key)
    file.content_type = content_type
    actual_key = storage.save(storage_key, file)
    if actual_key != storage_key:
        storage.delete(actual_key)
        msg = f"Storage key mismatch: expected {storage_key}, got {actual_key}"
        raise RuntimeError(msg)


def delete_from_storage(storage_keys: list[str]) -> None:
    """Best-effort deletion of storage objects (for cleanup on failure)."""
    storage = get_media_storage()
    for key in storage_keys:
        try:
            storage.delete(key)
        except Exception:
            logger.warning("Failed to delete storage key %s", key, exc_info=True)
