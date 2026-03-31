# Media Architecture Plan

Plan date: 2026-03-31

This document proposes a media architecture for Pinbase after the database reset. No migration/backfill is needed. Decisions are informed by reviewing the Flipfix sister project's production media system and adapting its patterns to Pinbase's claims-based architecture.

## Goals

- Allow Pinbase users to upload images (first PR) and video (follow-up) for MachineModel (first PR) then all catalog entity types (follow-up).
- Keep third-party media external. OPDB, IPDB, Fandom, Wikidata images stay where they are (`extra_data["opdb.images"]`, etc.). Never copy external images into Pinbase storage.
- Keep catalog truth claims-based. Media attachments, categories, and primary flags go through provenance.
- Separate catalog truth from storage infrastructure. Binary files, renditions, storage keys are infrastructure.
- Store relative object keys, not origin-specific URLs. CDN adoption becomes a config change.
- Keep the initial PR small: machine model images only.

## Non-Goals For The First PR

- No video upload flow.
- No support for non-MachineModel entity media UIs.
- No CDN cutover.
- No automatic import from current `extra_data` media into owned storage.
- No presigned direct-to-S3 uploads (added in video follow-up).
- No sha256 dedupe (potential far-future follow-up).
- No async task queue (added when video transcoding requires it).

## Ownership Boundary

The media system is for Pinbase-owned media only.

- Uploaded media goes into `MediaAsset` + `MediaVariant`.
- Pinbase-generated derivatives go into Pinbase storage.
- Pinbase serves URLs for those owned files.

Third-party media stays outside:

- OPDB images stay as OPDB image metadata in `extra_data`.
- IPDB images stay as IPDB image URLs.
- Fandom/Wikidata images stay as source references.

Pinbase does not download, transcode, re-host, or pretend to own third-party files.

UI and APIs prefer Pinbase-owned media first, then fall back to third-party referenced media.

## App Structure

All media models, APIs, and processing live in a new **`media` app** (`backend/apps/media/`). Media is a distinct domain — storage infrastructure, file processing, upload endpoints — and is big enough to warrant its own app rather than being folded into `catalog` or `core`.

Wiring between apps:

- **`media` app owns**: `MediaAsset`, `MediaVariant`, `EntityMedia`, image processing module, upload API endpoint.
- **`catalog` app owns**: `media_attachment` claim namespace registration (in `catalog/claims.py`, alongside credits/themes/etc.) and media claim resolution logic (in `catalog/resolve/`, since it already orchestrates all relationship resolution).
- **`EntityMedia`** uses a GenericFK to target catalog entities, so the `media` app has no import dependency on catalog models.

This mirrors how `provenance` works today — provenance owns the Claim model, catalog registers namespaces and runs resolution. Same pattern: media owns the storage/attachment models, catalog registers the claim namespace and resolves them.

## Data Model

### Three-Layer Architecture

1. **`MediaAsset`** — One logical Pinbase-owned uploaded media item (infrastructure).
2. **`MediaVariant`** — One physical stored file for that asset: original, thumbnail, display-size, and future video renditions (infrastructure).
3. **`EntityMedia`** — The resolved catalog attachment row linking a catalog entity to a media asset with category and primary metadata (catalog truth, claim-resolved).

This separation matters:

- `MediaAsset` and `MediaVariant` are infrastructure records, not catalog claims.
- `EntityMedia` is catalog truth and is materialized from claims.
- Third-party media references remain in claim-backed `extra_data`, not in `MediaAsset`.

### `MediaAsset`

Infrastructure record for one logical media item.

Fields:

- `id` (auto PK)
- `uuid` (UUIDField, unique, not null, default=uuid4)
- `kind`: `image` or `video` (CharField with choices, not null)
- `original_filename` (CharField, not null)
- `mime_type` (CharField, not null)
- `byte_size` (PositiveBigIntegerField, not null)
- `width` (PositiveIntegerField, nullable)
- `height` (PositiveIntegerField, nullable)
- `duration_seconds` (PositiveIntegerField, nullable — video only, future)
- `status`: `ready`, `processing`, `failed` (CharField with choices, not null)
- `uploaded_by` (FK to User, not null — every asset has an uploader)
- `created_at` (auto_now_add)
- `updated_at` (auto_now)

Database constraints:

- `field_not_blank("original_filename")` — no empty strings.
- `field_not_blank("mime_type")` — no empty strings.
- `original_filename` must contain at least one `.` — extensionless files are rejected at upload; enforce at DB level too.
- `byte_size > 0` — zero-byte files are never valid.
- `kind IN ('image', 'video')` — enforced at DB level, not just Django choices.
- `status IN ('ready', 'processing', 'failed')` — enforced at DB level.
- `width` and `height` must both be null or both be set — `(width IS NULL) = (height IS NULL)`.
- `width > 0` and `height > 0` when set — PositiveIntegerField allows 0, but a 0-pixel dimension is never valid.
- `duration_seconds > 0` when set — zero-length media is never valid.
- When `status = 'ready'` and `kind = 'image'`, `width` and `height` must be set — a ready image always has known dimensions.
- When `kind = 'image'`, `duration_seconds` must be null — images don't have duration.
- When `kind = 'image'`, `status != 'processing'` — images are processed synchronously, never enter processing state.
- `mime_type` must be consistent with `kind`: when `kind = 'image'`, `mime_type` must start with `image/`; when `kind = 'video'`, `mime_type` must start with `video/`.
- `uuid` UNIQUE (field-level).

Notes:

- Not a catalog claim. Pure infrastructure.
- `uploaded_by` is required (not nullable). Since we removed `source_kind`, every asset is a user upload.
- The `status` field exists for video support later. For images in the first PR, assets go straight to `ready` or `failed`.
- No `sha256` field in the first PR. Dedupe is a potential far-future follow-up.

### `MediaVariant`

Infrastructure record for one stored rendition of a media asset.

Fields:

- `id` (auto PK)
- `asset` (FK to `MediaAsset`, on_delete=CASCADE, related_name="variants", not null)
- `role` (CharField, not null — `original`, `thumb`, `display`; extended later with `poster`, `mp4`, etc.)
- `storage_key` (CharField, not null — relative path, never a full URL)
- `mime_type` (CharField, not null)
- `byte_size` (PositiveBigIntegerField, not null)
- `width` (PositiveIntegerField, nullable)
- `height` (PositiveIntegerField, nullable)
- `is_ready` (BooleanField, not null, default=True)
- `created_at` (auto_now_add)
- `updated_at` (auto_now)

Database constraints:

- `field_not_blank("role")` — no empty strings.
- `field_not_blank("storage_key")` — no empty strings.
- `field_not_blank("mime_type")` — no empty strings.
- `byte_size > 0` — zero-byte files are never valid.
- `width` and `height` must both be null or both be set — `(width IS NULL) = (height IS NULL)`.
- `width > 0` and `height > 0` when set — PositiveIntegerField allows 0, but a 0-pixel dimension is never valid.
- `storage_key` must start with `catalog-media/` — enforces key prefix convention at DB level.
- `storage_key` must not start with `http://` or `https://` — catches accidental full URL storage. Relative keys only.
- `storage_key` must not contain `..` — prevents path traversal.
- `storage_key` must not contain whitespace — catches encoding issues.
- UNIQUE `(asset, role)` — one variant per role per asset.
- `storage_key` UNIQUE (field-level) — no two variants share a storage path.

Notes:

- Shipping the variant table now avoids a migration when video support adds `poster`, `mp4`, `hls_playlist`, `hls_segment` roles.
- Public URL = `MEDIA_PUBLIC_BASE_URL + storage_key`.
- For images in the first PR, every successful upload creates exactly three variants: `original`, `thumb`, `display`.

### `EntityMedia`

Resolved catalog attachment row. This is what APIs and pages read.

Fields:

- `id` (auto PK)
- `content_type` (FK to ContentType, not null) + `object_id` (PositiveIntegerField, not null) — GenericForeignKey targeting any catalog entity.
- `asset` (FK to `MediaAsset`, on_delete=CASCADE, not null)
- `category` (CharField, nullable — entity-type-specific vocabulary; null means uncategorized)
- `is_primary` (BooleanField, not null, default=False)
- `created_at` (auto_now_add)
- `updated_at` (auto_now)

Database constraints:

- UNIQUE `(content_type, object_id, asset)` — one attachment per entity-asset pair. Prevents the same image from being attached twice to the same entity.
- Partial UNIQUE `(content_type, object_id, category)` WHERE `is_primary = TRUE AND category IS NOT NULL` — at most one primary image per entity per category.
- Partial UNIQUE `(content_type, object_id)` WHERE `is_primary = TRUE AND category IS NULL` — at most one uncategorized primary per entity. Needed because PostgreSQL treats `NULL != NULL` in unique constraints, so the previous constraint alone would allow multiple uncategorized primaries.
- When `category` is not null, it must not be blank — `category IS NULL OR category != ''`. No empty-string categories; use null for uncategorized.
- `object_id > 0` — valid entity PKs are always positive.

Application-level validation (not expressible as DB constraints):

- `category` must be in the allowed set for the entity's content type (checked at claim assertion time via the `MEDIA_CATEGORIES` registry).
- `asset.kind` must be compatible with the category registry for the entity type (e.g., MachineModel image categories don't apply to video assets).

`EntityMedia` is materialized from claims, not hand-edited.

## Claims Design

Media attachment facts go through provenance. This follows the existing relationship-claim pattern in `catalog/claims.py`.

### Claim Shape

Add a new relationship namespace `media_attachment`. The claim identity is the `MediaAsset` PK. The value dict contains:

```python
{
    "media_asset": <asset_pk>,
    "category": "backglass",       # nullable
    "is_primary": True,
    "exists": True,
}
```

The `claim_key` encodes the identity: `media_attachment|media_asset:<pk>`.

### Resolution

Resolution works in two stages:

1. **Per-attachment**: Resolve the winning claim per attachment identity (standard claim resolution — highest priority, most recent).
2. **Primary enforcement**: Within the resolved set, enforce primary constraints deterministically. If two resolved attachments both claim `is_primary=true` for the same `(entity, category)`, pick the highest-priority winner for that category and materialize the others as non-primary.

This keeps the claims model coherent without treating primary selection as a separate mutable side channel.

### Registration

Register the namespace in `catalog/claims.py` alongside existing relationship namespaces:

```python
# In ENTITY_REF_TARGETS or a similar registration:
"media_attachment": [RefKey("media_asset", MediaAsset)],
```

And call `register_relationship_targets()` from `CatalogConfig.ready()` as usual.

## Category Registry

Image categories are entity-type-specific, not a global enum.

First PR implements only `MachineModel`:

- `backglass`, `playfield`, `cabinet`, `other`

This mirrors OPDB's useful structure. The constraint is "at most one primary image per `(model, category)`".

Follow-up category sets (guesses, not commitments):

- `Manufacturer`: `logo`, `building`, `product`, `other`
- `CorporateEntity`: `logo`, `building`, `document`, `other`
- `Person`: `portrait`, `signature`, `other`
- `Title`: `logo`, `hero`, `other`
- Other entity types as needed.

Implementation: a simple `MEDIA_CATEGORIES` dict mapping entity model classes to lists of allowed category strings. Validated at claim assertion time — reject unknown categories immediately, don't let them into the claims table.

## Upload Flow (First PR — Images)

Upload through Django, not presigned URLs. For images (typically 1-10MB), this is one round trip and avoids the complexity of presigned URL flows, S3 CORS configuration, and partial-upload error handling. Since we use django-storages with S3 from day one, the files end up in S3 regardless — switching to presigned URLs later changes the upload _path_ but not where files are stored. No migration needed.

### Flow

1. **Client** POSTs multipart form to `POST /api/media/upload/` with the image file.
2. **Backend** validates the file (type, size, decodability).
3. **Backend** processes the image synchronously: generates `thumb` and `display` variants using Pillow (EXIF transpose, LANCZOS resize, WebP output).
4. **Backend** uploads all three files (original, thumb, display) to R2 via django-storages.
5. **Backend** creates `MediaAsset` (status=`ready`) + 3 `MediaVariant` rows in a single database transaction.
6. **Backend** returns the asset UUID and variant URLs.
7. **Client** creates/updates the media attachment claim on the target entity via the existing claim-patch API (or a new dedicated endpoint).
8. **Resolution** materializes `EntityMedia`.

Steps 1-6 are one synchronous HTTP request. No task queue, no polling, no "pending" state for images.

### Atomicity and Failure Handling

The upload flow must not leave orphaned state on failure:

- **Processing failure** (Pillow can't generate derivatives): return error, nothing written to S3 or DB.
- **S3 write failure** (one of the three uploads fails): clean up any S3 objects already written, return error, nothing written to DB.
- **DB write failure** (transaction fails after S3 uploads succeed): clean up all S3 objects. DB transaction rollback handles the rows.

The key invariant: **DB rows are only created after all S3 objects are successfully written.** This means orphaned DB rows can't exist. Orphaned S3 objects (written but DB transaction failed) are cleaned up in the error handler. A periodic cleanup job for orphaned S3 objects is not needed in the first PR but is a reasonable follow-up if operational experience shows leakage.

### Why Synchronous Processing For Images

Flipfix processes images in `model.save()` synchronously and it works well in production. For thumbnail + display generation, Pillow processing takes under a second. Async processing would add a task queue dependency, status polling UI, and "pending" states — unnecessary complexity for images.

Async processing is reserved for video transcoding (follow-up PR), where it genuinely matters.

### Upload Validation

Strict validation on upload — reject early, reject clearly:

- **Authentication**: user must be logged in. Anonymous uploads are never allowed.
- **File presence**: request must contain exactly one file.
- **File extension**: must be in `ALLOWED_IMAGE_EXTENSIONS` (see Accepted Image Formats below). Reject unknown extensions even if the content looks valid — defense in depth.
- **Pillow decodability**: `Image.open()` must succeed. This is the real validation — catches corrupt files, truncated uploads, and non-images regardless of extension or content-type header.
- **File size**: configurable max (e.g. 20MB for images). Enforced both in Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` and explicitly in the view. Return a clear error, not a generic 413.
- **Dimensions after decode**: reject degenerate images (0×0, 1×1). Set a reasonable max dimension (e.g. 20000×20000) to prevent memory bombs during processing.
- **MIME type derivation**: the Pillow-detected format is the canonical source of truth for the persisted `mime_type` on `MediaAsset` and `MediaVariant`. Client-provided content-type headers and file extensions are used for initial filtering only, never persisted.

### Accepted Image Formats

Defined once in the media app's constants module, matching flipfix's proven set:

```python
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",  # Web-native
    ".heic", ".heif",                           # iPhone photos
    ".avif",                                    # Modern compression
    ".bmp",                                     # Legacy, converted to JPEG
}
```

| Upload format            | Preserved or converted | Output format     | Notes                                         |
| ------------------------ | ---------------------- | ----------------- | --------------------------------------------- |
| JPEG (.jpg, .jpeg)       | Preserved              | JPEG (quality=85) | Most common upload format                     |
| PNG                      | Preserved              | PNG               | Transparency preserved                        |
| WebP                     | Preserved              | WebP (quality=80) |                                               |
| AVIF                     | Preserved              | AVIF (quality=63) |                                               |
| HEIC/HEIF (.heic, .heif) | Converted              | JPEG              | iPhone default format; requires `pillow-heif` |
| GIF                      | Converted              | JPEG              | Static frame only; animated GIF not supported |
| BMP                      | Converted              | JPEG              | Legacy format                                 |

Derivatives (thumb, display) are always WebP regardless of original format.

HEIC support requires `pillow-heif`, a Pillow plugin that registers HEIC/HEIF format handlers. This is the same approach flipfix uses in production.

## Image Processing

Adapted from flipfix's `core/image_processing.py` — a production-proven Pillow pipeline.

### Processing Steps

1. Validate image type and decodability (Pillow `Image.open()`).
2. EXIF orientation correction (`ImageOps.exif_transpose()`).
3. Extract dimensions, mime type, byte size.
4. Generate two derivatives:
   - **`thumb`**: max 400px longest side, WebP output. For grid/list views.
   - **`display`**: max 1600px longest side, WebP output. For detail pages.
5. Save original in uploaded format, derivatives in WebP.

### Format Handling (from flipfix)

- **Original**: web-native formats preserved as-is; non-web formats (HEIC/HEIF, BMP, GIF) converted to JPEG. PNG with transparency stays PNG regardless. See the Accepted Image Formats table for the full mapping.
- **Derivatives** (thumb, display): always WebP output.
- LANCZOS resampling for resize.
- Pillow `optimize` flag for JPEG/PNG.

### Dimensions

- `THUMB_MAX_DIMENSION = 400` (smaller than flipfix's 800 — Pinbase grid items are smaller)
- `DISPLAY_MAX_DIMENSION = 1600` (smaller than flipfix's 2400 — web display, not print)

These can be tuned after seeing real usage.

## Storage

### Cloudflare R2 via django-storages

Use **Cloudflare R2** as the storage backend, accessed through `django-storages` with the S3-compatible API. R2 is the recommended provider because:

- **We already have it** — Pinbase pulls ingest sources from an R2 bucket today. Same Cloudflare account, new bucket (or same bucket, different prefix).
- **Zero egress fees** — for a media-heavy catalog site, this matters. Every thumbnail in a grid view, every hero image on a detail page — free to serve.
- **Hosting-independent** — R2 is durable storage decoupled from Railway. If we change hosting providers, media doesn't move.
- **Integrated CDN path** — Cloudflare's CDN (free tier) sits natively in front of R2. No cross-provider wiring needed. When CDN time comes, it's a DNS change, not an architecture change.

Using django-storages with R2's S3-compatible API also gives us:

- Same file locations whether uploaded through Django or later via presigned URLs. No migration needed when switching upload path.
- Swappable to any other S3-compatible service if needed (AWS S3, Backblaze B2, etc.).

### Key Pattern

```text
catalog-media/{asset_uuid}/original/{filename}
catalog-media/{asset_uuid}/thumb.webp
catalog-media/{asset_uuid}/display.webp
```

Future video variants:

```text
catalog-media/{asset_uuid}/poster.webp
catalog-media/{asset_uuid}/master.mp4
catalog-media/{asset_uuid}/hls/master.m3u8
catalog-media/{asset_uuid}/hls/720p/segment-0001.ts
```

### URL Generation

- Database stores `storage_key` (relative path), never full URLs.
- Public URL = `settings.MEDIA_PUBLIC_BASE_URL + storage_key`.
- Today: `MEDIA_PUBLIC_BASE_URL` points at the R2 bucket's public origin.
- Later: point a custom domain (e.g. `media.pinbase.app`) through Cloudflare DNS, which automatically enables the CDN. Change one env var, no database rewrite.

### Local Development

Use MinIO (S3-compatible, runs in Docker) or Django's default `FileSystemStorage` with a local `MEDIA_ROOT`. The storage key pattern is the same either way — only the backend differs.

## Serving

Django is not the hot-path media file server.

### API Response Shape

APIs return media metadata plus public URLs for ready variants:

```json
{
  "owned_media": [
    {
      "asset_uuid": "abc-123",
      "kind": "image",
      "category": "backglass",
      "is_primary": true,
      "variants": {
        "thumb": "https://media.pinbase.app/catalog-media/abc-123/thumb.webp",
        "display": "https://media.pinbase.app/catalog-media/abc-123/display.webp",
        "original": "https://media.pinbase.app/catalog-media/abc-123/original/backglass.jpg"
      }
    }
  ],
  "hero_image_url": "...",
  "thumbnail_url": "..."
}
```

### Fallback Policy

1. Prefer Pinbase-owned media from `EntityMedia`.
2. If no owned media exists for the needed slot, fall back to third-party referenced media from `extra_data` (`opdb.images`, `ipdb.image_urls`).

The existing `_extract_image_urls()` helper in `catalog/api/helpers.py` handles the external fallback. The new code adds an owned-media-first layer on top.

### Ordering

API responses return media in deterministic order: primary first, then by `created_at` ascending. This applies both to the `owned_media` list in entity detail responses and to any future media listing endpoint. Pagination is not needed in the first PR — MachineModel images will be single-digit counts per entity.

## Authorization

For the first PR, media follows the same rules as all other claim types:

- **Upload**: any authenticated user. Anonymous uploads are never allowed.
- **Attach / detach / set primary / change category**: any authenticated user, same as credits, themes, and other claim types. Claims go through provenance, and resolution picks winners by priority.
- **Delete underlying asset**: only the original uploader or staff can delete a `MediaAsset`. Deletion is only allowed when the asset has no active attachment claims on any entity (see Deletion Policy below).

The broader user-role/permission landscape (tiered permissions, who can retract whose claims, moderation workflows) is a cross-cutting concern that applies to all claim types, not just media. That is a separate follow-up discussion.

## Rate Limits

Basic per-user upload rate limiting to protect storage costs and moderation workload:

- Per-user upload limit: `MAX_UPLOADS_PER_HOUR = 60`, defined once in the media app's constants module.
- Enforced at the upload endpoint. Return 429 with a clear error message including when the user can retry.
- Implementation: Django cache-based rate limiting (no new infrastructure).

Per-entity attachment limits and more sophisticated quota systems are deferred until real usage patterns emerge.

## Deletion Policy

Media deletion has two distinct operations:

### Detach (deactivate attachment claim)

Deactivating a `media_attachment` claim removes the `EntityMedia` row on next resolution. The underlying `MediaAsset` and its S3 files are **not** deleted — the asset may be attached to other entities, and the claim history is preserved in provenance.

### Delete asset

Deleting a `MediaAsset` is a hard delete that removes:

1. All `MediaVariant` rows (CASCADE).
2. All S3 objects for those variants.
3. The `MediaAsset` row itself.

Preconditions for asset deletion:

- The asset must have **no active attachment claims** on any entity. If active claims exist, the delete request is rejected with an error listing the entities.
- Only the original uploader or staff can delete.

There is no soft-delete or tombstone for `MediaAsset`. Assets are infrastructure, not catalog truth — provenance is preserved in the claim history (deactivated claims remain in the database), not in the asset row.

## Frontend Architecture

### Component Decomposition

All media UI is built as decomposed SvelteKit components with logic extracted to TypeScript files for testability. Interaction patterns are adapted from flipfix (upload -> poll -> update) but implemented in Svelte 5 runes mode.

#### TypeScript Modules (logic, testable without DOM)

- **`media-upload.ts`** — Upload state machine, file validation, API calls. Exports reactive state and action functions.
- **`media-api.ts`** — API client functions for media endpoints (upload, attach, delete).
- **`media-types.ts`** — TypeScript types for media API responses, generated from OpenAPI schema.

#### Svelte Components (thin UI wrappers)

- **`MediaUploadButton.svelte`** — File picker trigger + drag-drop zone. Calls into `media-upload.ts`.
- **`MediaUploadProgress.svelte`** — Upload progress indicator (synchronous for images, polling for future video).
- **`MediaGrid.svelte`** — Grid of media items with delete and set-primary actions.
- **`MediaCard.svelte`** — Single media item card (thumbnail, category badge, primary indicator).
- **`MediaAttachForm.svelte`** — Form for setting category and primary flag on an attachment.
- **`HeroImage.svelte`** — Detail page hero image with owned-first/external-fallback logic.

#### Interaction Flow (Image Upload)

1. User clicks upload button or drags file onto drop zone.
2. `media-upload.ts` validates file client-side (type, size).
3. `media-upload.ts` calls `POST /api/media/upload/` with the file.
4. On success, component shows the returned thumbnail immediately.
5. User selects category and optionally sets primary flag.
6. `media-api.ts` calls the claim-patch endpoint to create the media attachment claim.
7. On success, `MediaGrid` updates to show the new attachment.

For the first PR, there is no polling step — image processing is synchronous. The polling pattern (`media-upload.ts` watches for status transitions via `GET /api/media/{uuid}/status/`) is scaffolded but only activated when video support lands.

## Testing Strategy

### Patterns Adapted From Flipfix

#### Test Utilities

- **`TemporaryMediaMixin`** — Creates a temp directory for `MEDIA_ROOT`, cleans up after test class. Adapted from flipfix's `core/test_utils.py`.
- **`create_uploaded_image()`** — Creates a PIL Image as a `BytesIO` with `.name` attribute, suitable for Django upload testing. Directly from flipfix.
- **`MINIMAL_PNG`** — Minimal valid PNG bytes for tests that need valid image data without Pillow.

#### Backend Tests

- **Image processing unit tests**: Resize, EXIF transpose, format conversion, transparency handling. Test the processing module in isolation (no Django models).
- **Upload API tests**: POST valid/invalid files, check MediaAsset + MediaVariant creation, verify S3 storage keys.
- **Claim + resolution tests**: Assert media attachment claims, resolve, verify EntityMedia rows. Test primary constraint enforcement.
- **API response tests**: Verify owned-media-first fallback to external. Verify variant URLs in response.
- **File validation tests**: Rejected file types, oversized files, corrupt files.

#### Frontend Tests

- **TypeScript module tests** (vitest): Test `media-upload.ts` state machine, `media-api.ts` API calls (mocked fetch), validation logic. These are the high-value tests — logic without DOM.
- **Component tests** (vitest + testing-library): Basic render tests for `MediaGrid`, `MediaCard`. Not exhaustive — the logic is in the TypeScript modules.

### Mocking Strategy

- **S3 storage**: Use `django.core.files.storage.InMemoryStorage` or `TemporaryMediaMixin` with `FileSystemStorage` in tests. Never hit real S3.
- **Image processing**: Test the processing module with real Pillow (it's fast). Don't mock Pillow.
- **API calls in frontend**: Mock `fetch` in vitest for `media-api.ts` tests.

## Django Configuration

### New Dependencies

- `django-storages[s3]` — S3 storage backend.
- `Pillow` — Image processing (may already be present).
- `pillow-heif` — HEIC/HEIF support for Pillow (iPhone photos). Registers format handlers on import.
- `boto3` — S3 client (pulled in by django-storages).

### Settings

```python
# Storage — Cloudflare R2 via S3-compatible API
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        # existing WhiteNoise config
    },
}

# Cloudflare R2 (S3-compatible)
AWS_STORAGE_BUCKET_NAME = env("R2_BUCKET_NAME")
AWS_S3_REGION_NAME = "auto"  # R2 always uses "auto"
AWS_S3_ENDPOINT_URL = env("R2_ENDPOINT_URL")  # https://<account_id>.r2.cloudflarestorage.com
AWS_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY")

# Media URL generation
MEDIA_PUBLIC_BASE_URL = env("MEDIA_PUBLIC_BASE_URL")
# Production: "https://media.pinbase.app/" (custom domain via Cloudflare CDN)
# Or R2 public bucket URL until custom domain is set up
```

For local development with MinIO or filesystem:

```python
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_PUBLIC_BASE_URL = "/media/"
```

## Initial PR Scope

### Include

- `MediaAsset`, `MediaVariant`, `EntityMedia` models + migrations.
- `media_attachment` claim namespace registration + validation.
- Resolver support for media attachment claims (including primary enforcement).
- Machine-model image category registry (`backglass`, `playfield`, `cabinet`, `other`).
- Image processing module (adapted from flipfix).
- Upload API endpoint (`POST /api/media/upload/`).
- Media attachment claim endpoint (or extend existing claim-patch).
- API response support: owned media first, external fallback second.
- django-storages + Cloudflare R2 configuration.
- Frontend: `MediaUploadButton`, `MediaGrid`, `MediaCard`, `MediaAttachForm`, `HeroImage`.
- Frontend: `media-upload.ts`, `media-api.ts` TypeScript modules.
- Tests: image processing, upload API, claims + resolution, API responses, frontend TypeScript modules.

### Exclude

- Videos.
- Non-MachineModel entity media UIs.
- Presigned direct-to-S3 uploads.
- CDN setup.
- Import migration from `extra_data` media.
- sha256 dedupe.
- Async task queue.

## Follow-Up Work

### Follow-Up 1: Video Support

- Presigned direct-to-S3 uploads (needed for large video files — no migration, same S3 bucket).
- Async task queue (evaluate options: Celery, django-q2, or lighter-weight).
- Video transcoding worker: poster frame + MP4 fallback (adapted from flipfix's `core/transcoding.py`).
- Full status state machine: `pending` -> `processing` -> `ready` / `failed`.
- Frontend polling pattern activation in `media-upload.ts`.
- `VideoPlayer.svelte` component with transcode state handling (adapted from flipfix's video player patterns).
- HLS adaptive streaming only if demand justifies operational cost.

### Follow-Up 2: Other Entity Types

- Manufacturer, CorporateEntity, Person, Title, Series, Franchise, System, Location media UIs.
- Entity-specific category registries.

### Follow-Up 3: External Reference Cleanup

- Normalize third-party media reference shapes across OPDB/IPDB/Fandom/Wikidata.
- Centralize "owned first, external fallback second" media selection in one helper.

### Follow-Up 4: CDN Cutover

- Point a custom domain (e.g. `media.pinbase.app`) through Cloudflare DNS — this automatically enables Cloudflare's CDN in front of R2 (free tier, zero additional cost).
- Switch `MEDIA_PUBLIC_BASE_URL` to the custom domain.
- Configure cache headers and optional purge hooks.

### Follow-Up 5: User Roles and Permissions

- Design a cross-cutting user-role/permission model that applies to all claim types (not just media).
- Topics: tiered permissions, who can retract whose claims, moderation workflows, promotion paths.
- This is a broader product decision that should be considered as a whole rather than decided piecemeal per feature.

### Follow-Up 6 (Far Future): Dedupe

- Add `sha256` field to `MediaAsset`.
- Compute hash on upload, check for existing asset.
- Decide UX: block duplicate, reuse existing asset, or warn.

## Key Design Decisions

| Decision               | Choice                                    | Rationale                                                                                                                                          |
| ---------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Upload path (first PR) | Django relay                              | One round trip, simpler than presigned URLs. Fine for images (1-10MB). Switch to presigned for video — no migration since files are already in S3. |
| Image processing       | Synchronous in upload request             | Under 1 second for thumb + display. Avoids task queue dependency. Flipfix proves this works in production.                                         |
| Variant storage        | `MediaVariant` table                      | Small overhead now, avoids migration when video adds poster/mp4/hls roles.                                                                         |
| Status field           | Present but minimal                       | `ready`/`failed` for images. Full state machine activated for video follow-up.                                                                     |
| sha256 dedupe          | Deferred (far future)                     | Adds complexity without clear near-term value.                                                                                                     |
| Task queue             | Deferred (video follow-up)                | No async work in first PR. Evaluate options when video lands.                                                                                      |
| Derivative format      | WebP                                      | Good compression, universal browser support. AVIF deferred.                                                                                        |
| Storage provider       | Cloudflare R2                             | Already in use for ingest sources. Zero egress, hosting-independent, integrated CDN path (free).                                                   |
| Third-party media      | Stays in `extra_data`                     | Not temporary — permanent fallback layer. API reads both owned and external.                                                                       |
| Category vocabulary    | Per-entity-type registry                  | Not a global enum. `MachineModel` gets `backglass`/`playfield`/`cabinet`/`other`.                                                                  |
| Frontend architecture  | Logic in TypeScript, thin Svelte wrappers | Testable without DOM. Follows flipfix's interaction patterns in Svelte 5 runes.                                                                    |
