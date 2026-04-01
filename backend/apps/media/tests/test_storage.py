"""Tests for media storage key generation and URL building (TDD: written before implementation)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.media.storage import build_public_url, build_storage_key, upload_to_storage


class TestBuildStorageKey:
    """build_storage_key() derives deterministic paths from asset UUID + rendition type."""

    def test_original_includes_filename(self):
        asset_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        key = build_storage_key(asset_uuid, "original", "backglass.jpg")
        assert (
            key == "media/12345678-1234-5678-1234-567812345678/original/backglass.jpg"
        )

    def test_thumb_ignores_filename(self):
        asset_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        key = build_storage_key(asset_uuid, "thumb", "anything.png")
        assert key == "media/12345678-1234-5678-1234-567812345678/thumb.webp"

    def test_display_ignores_filename(self):
        asset_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        key = build_storage_key(asset_uuid, "display", "anything.png")
        assert key == "media/12345678-1234-5678-1234-567812345678/display.webp"

    def test_converted_extension(self):
        """BMP→JPEG conversion: stored filename uses .jpg, not .bmp."""
        asset_uuid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        key = build_storage_key(asset_uuid, "original", "photo.jpg")
        assert key.endswith("/original/photo.jpg")

    def test_whitespace_in_filename_rejected(self):
        asset_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        with pytest.raises(ValueError, match="whitespace"):
            build_storage_key(asset_uuid, "original", "bad file.jpg")

    def test_invalid_rendition_type_rejected(self):
        asset_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        with pytest.raises(ValueError, match="rendition_type"):
            build_storage_key(asset_uuid, "poster", "image.jpg")

    def test_empty_filename_rejected(self):
        asset_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        with pytest.raises(ValueError, match="stored_filename"):
            build_storage_key(asset_uuid, "original", "")

    def test_slash_in_filename_rejected(self):
        asset_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        with pytest.raises(ValueError, match="path separator"):
            build_storage_key(asset_uuid, "original", "sub/dir.jpg")


class TestBuildPublicUrl:
    """build_public_url() concatenates base URL + storage key."""

    @override_settings(MEDIA_PUBLIC_BASE_URL="https://media.example.com/")
    def test_basic_url(self):
        url = build_public_url("media/abc/thumb.webp")
        assert url == "https://media.example.com/media/abc/thumb.webp"

    @override_settings(MEDIA_PUBLIC_BASE_URL="https://media.example.com")
    def test_base_url_without_trailing_slash(self):
        url = build_public_url("media/abc/thumb.webp")
        assert url == "https://media.example.com/media/abc/thumb.webp"

    @override_settings(MEDIA_PUBLIC_BASE_URL="/media/")
    def test_relative_base_url(self):
        url = build_public_url("media/abc/thumb.webp")
        assert url == "/media/media/abc/thumb.webp"


class TestUploadToStorage:
    """upload_to_storage() detects key mismatches from the storage backend."""

    def test_key_mismatch_raises_and_cleans_up(self):
        mock_storage = MagicMock()
        mock_storage.save.return_value = "media/abc/thumb_renamed.webp"

        with patch("apps.media.storage.get_media_storage", return_value=mock_storage):
            with pytest.raises(RuntimeError, match="Storage key mismatch"):
                upload_to_storage("media/abc/thumb.webp", b"data", "image/webp")

        # The mismatched key should be cleaned up
        mock_storage.delete.assert_called_once_with("media/abc/thumb_renamed.webp")

    def test_matching_key_succeeds(self):
        mock_storage = MagicMock()
        mock_storage.save.return_value = "media/abc/thumb.webp"

        with patch("apps.media.storage.get_media_storage", return_value=mock_storage):
            upload_to_storage("media/abc/thumb.webp", b"data", "image/webp")

        mock_storage.delete.assert_not_called()
