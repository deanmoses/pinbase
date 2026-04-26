# API Schema Naming Rationalization

## Context

The Django Ninja schema names that flow through OpenAPI into the
generated TypeScript types are inconsistent and noisy. Today the
contract carries:

- 117 names ending in `Schema` (a Ninja base-class artifact, not
  domain vocabulary).
- 18 names that don't — split between intentional choices (`Ref`),
  divergent media-app conventions (`UploadOut`, `MediaAssetRefIn`,
  `RenditionUrlsOut`, `AttachmentMetaOut`), and generic Python-side
  leakage (`Input`, `JsonBody`).
- Schemas with too-generic bare names that survive suffix removal
  poorly (`Variant`, `Source`, `Stats`, `Recognition`, `Create`).
- Schemas defined inline in endpoint files that don't follow the
  schema-module convention (out of scope for this plan; see
  follow-ups).

The OpenAPI contract is the shared vocabulary between Django, the generated TypeScript types, ~88 frontend consumers, and any AI agent reading the codebase. When the same role (input, output, list-row, detail) carries three different suffixes depending on which app a schema lives in, every contributor has to learn the per-app convention before they can type anything correctly. The Schema suffix is implementation noise — it names the Pydantic parent class, not the domain concept — and it adds friction to every read of every type signature. Generic names like Input, Source, Stats are worse: at the OpenAPI component level they're ambiguous, and a frontend reader can't tell what they refer to without grepping the backend.

The cost compounds over time. Every new schema either follows whichever local convention the surrounding file uses (perpetuating the divergence) or invents its own. Renaming gets monotonically harder: the longer we wait, the more consumers reference each schema. And the inconsistency blocks lint enforcement — there's no single convention for a boundary test to assert, so drift goes uncaught.

We will rationalize the names at the
source — in the backend Python classes — so the OpenAPI contract,
the generated `schema.d.ts`, and the frontend imports all use the
same names.

This is part of the [ApiSvelteBoundary.md](ApiSvelteBoundary.md) work. In [ApiSvelteBoundary.md](ApiSvelteBoundary.md)'s task sequence, this is the
_Rename API schemas on the backend_ task: _Re-export barrel_ lands
first so per-rename diffs stay small, _Type error responses_ lands
ahead of the rename so its correctness fix ships sooner and any
new error schemas get caught up in the rename pass, and
_Boundary tests_ inverts its `Schema`-suffix rule to enforce the
new convention.

## Naming convention

These rules apply to every Ninja schema class in `backend/apps/*`
and `backend/config/api.py`.

### Suffixes by role

| Role                                  | Suffix                                        | Example                         |
| ------------------------------------- | --------------------------------------------- | ------------------------------- |
| Output, full entity (detail)          | `…Detail`                                     | `TitleDetail`, `PersonDetail`   |
| Output, list/index page row           | `…ListItem` _or_ bare entity name (see below) | `TitleListItem`                 |
| Output, grid view row                 | `…GridItem`                                   | `PersonGridItem`                |
| Output, paginated/wrapped list        | `…List`                                       | `MachineModelList`              |
| Output, minimal reference (name+slug) | `Ref` or `…Ref`                               | `Ref`, `TitleRef`, `ModelRef`   |
| Input, full payload                   | `…Input`                                      | `ChangeSetInput`, `CreditInput` |
| Input, partial update                 | `…Patch`                                      | `ClaimPatch`, `TitleClaimPatch` |
| Input, create payload                 | `…Create`                                     | `SystemCreate`                  |

### Hard rules

1. **No `Schema` suffix anywhere.** It's a Ninja base-class artifact,
   not domain vocabulary.
2. **No `In`/`Out` suffixes.** Use `…Input` / bare-output. The
   media app's current `…In`/`…Out` names are migrated.
3. **Bare entity names are reserved for full canonical outputs.**
   Where an entity's "bare" schema today is actually a list-item
   shape (e.g., today's `PersonSchema`, `ManufacturerSchema`), it
   gets renamed to `…ListItem`. The bare
   name then becomes available for the canonical full shape — but
   the codebase doesn't currently use it that way, so the rename
   table below leaves the bare slot vacant in those cases. A future
   pass can decide whether to alias `Person` → `PersonDetail` or
   leave them distinct.
4. **Generic names get scoped.** `Variant`, `Source`, `Stats`,
   `Recognition`, and `Create` are too generic at the OpenAPI
   component level. Each is renamed to an entity-scoped name.
5. **`…Detail` is preserved as-is** for full-entity output shapes
   (see the page-vs-resource note below for the page-API context).

### Page-vs-resource note

[docs/ApiDesign.md](../../../ApiDesign.md) draws a sharp distinction
between resource APIs (`/api/<entity>/...`) and page APIs
(`/api/pages/<entity>/...`), with page endpoints returning
"page models." In practice, every `*DetailSchema` in the codebase
today is shared between the two — the page endpoint returns the
same shape as the resource detail endpoint. This plan does not
attempt to separate them. The rename preserves whatever sharing
exists; if a future pass splits page models from resource shapes,
it will introduce new `…Page` schemas alongside the `…Detail`
ones.

## Decisions baked into the rename table

These are settled in this plan; the per-app rename tables below
apply them mechanically.

| Current name               | New name                       | Why                                                                                                                                                                                           |
| -------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VariantSchema`            | `MachineModelVariant`          | Bare `Variant` collides with broader vocabulary; user rule reserves "variant" for machine model variants specifically.                                                                        |
| `SourceSchema`             | `CitationSource`               | Bare `Source` is too generic at the OpenAPI level. Aligns with the citation-app naming.                                                                                                       |
| `StatsSchema`              | `SiteStats`                    | Bare `Stats` is too generic. The schema lives in `config/api.py` and reports site-wide totals.                                                                                                |
| `RecognitionSchema`        | `CitationRecognition`          | Bare `Recognition` is too generic; clearly a citation-domain schema.                                                                                                                          |
| `Input` (auto)             | `PaginationParams`             | Ninja auto-named the inline pagination query model; give it a real name.                                                                                                                      |
| `JsonBody`                 | (removed from OpenAPI)         | A `apps/core/types.py` Python type alias leaking into OpenAPI as `{ [key: string]: unknown }`. The endpoint exposing it should declare a real schema or `dict[str, Any]` typed appropriately. |
| `UploadOut`                | `Upload`                       | Drop `Out` suffix. No collision with `UploadedMedia`.                                                                                                                                         |
| `UploadedMediaSchema`      | `UploadedMedia`                | Drop `Schema`.                                                                                                                                                                                |
| `MediaAssetRefIn`          | `MediaAssetRefInput`           | Standardize on `…Input`.                                                                                                                                                                      |
| `AttachmentMetaOut`        | `AttachmentMeta`               | Drop `Out` suffix.                                                                                                                                                                            |
| `RenditionUrlsOut`         | `RenditionUrls`                | Drop `Out` suffix.                                                                                                                                                                            |
| `BatchCitationInstanceOut` | `BatchCitationInstance`        | Drop `Out` suffix.                                                                                                                                                                            |
| `CitationInstanceCreateIn` | `CitationInstanceCreate`       | Use `…Create` for entity-scoped create input.                                                                                                                                                 |
| `EditOptionItem`           | `EditOption`                   | `Item` is redundant.                                                                                                                                                                          |
| `CreateSchema`             | `EntityCreateInput`            | Currently a base class for entity creates in `catalog/api/schemas.py`. Scoped name avoids collision with per-entity `…Create` names.                                                          |
| `SearchResponse`           | `CitationSourceSearchResponse` | `Response` suffix is rare; scope it to its entity since `SearchResponse` is too generic.                                                                                                      |

Names that already conform and pass through unchanged
(`EditCitationInput`, `CreditInput`, `GameplayFeatureInput`,
`FieldConstraint`, `Ref`, `*AncestorRef`, `*ChildRef`) are not
listed in the table above.

## Per-app rename tables

Apps are listed smallest first, matching the commit sequence below.

### `accounts` (4 schemas)

| Current                    | New                  |
| -------------------------- | -------------------- |
| `AuthStatusSchema`         | `AuthStatus`         |
| `EntityContributionSchema` | `EntityContribution` |
| `UserChangeSetSchema`      | `UserChangeSet`      |
| `UserProfileSchema`        | `UserProfile`        |

### `core` (4 schemas)

| Current                     | New           |
| --------------------------- | ------------- |
| `ErrorDetailSchema`         | `ErrorDetail` |
| `LinkTargetSchema`          | `LinkTarget`  |
| `LinkTargetsResponseSchema` | `LinkTargets` |
| `LinkTypeSchema`            | `LinkType`    |

### `media` (6 schemas)

| Current                 | New                  |
| ----------------------- | -------------------- |
| `AttachmentMetaOut`     | `AttachmentMeta`     |
| `MediaAssetRefIn`       | `MediaAssetRefInput` |
| `MediaRenditionsSchema` | `MediaRenditions`    |
| `RenditionUrlsOut`      | `RenditionUrls`      |
| `UploadOut`             | `Upload`             |
| `UploadedMediaSchema`   | `UploadedMedia`      |

### `citation` (15 schemas)

| Current                          | New                            |
| -------------------------------- | ------------------------------ |
| `CitationSourceChildSchema`      | `CitationSourceChild`          |
| `CitationSourceCreateSchema`     | `CitationSourceCreate`         |
| `CitationSourceDetailSchema`     | `CitationSourceDetail`         |
| `CitationSourceLinkCreateSchema` | `CitationSourceLinkCreate`     |
| `CitationSourceLinkSchema`       | `CitationSourceLink`           |
| `CitationSourceLinkUpdateSchema` | `CitationSourceLinkUpdate`     |
| `CitationSourceMatchSchema`      | `CitationSourceMatch`          |
| `CitationSourceParentSchema`     | `CitationSourceParent`         |
| `CitationSourceSearchSchema`     | `CitationSourceSearch`         |
| `CitationSourceUpdateSchema`     | `CitationSourceUpdate`         |
| `ExtractDraftSchema`             | `ExtractDraft`                 |
| `ExtractRequestSchema`           | `ExtractRequest`               |
| `ExtractResponseSchema`          | `ExtractResponse`              |
| `RecognitionSchema`              | `CitationRecognition`          |
| `SearchResponse`                 | `CitationSourceSearchResponse` |

### `provenance` (27 schemas)

| Current                        | New                      |
| ------------------------------ | ------------------------ |
| `AttributionSchema`            | `Attribution`            |
| `BatchCitationInstanceOut`     | `BatchCitationInstance`  |
| `ChangeSetBaseSchema`          | `ChangeSetBase`          |
| `ChangeSetDetailSchema`        | `ChangeSetDetail`        |
| `ChangeSetInputSchema`         | `ChangeSetInput`         |
| `ChangeSetListSchema`          | `ChangeSetList`          |
| `ChangeSetSchema`              | `ChangeSet`              |
| `ChangeSetSummarySchema`       | `ChangeSetSummary`       |
| `ChangeSetWithEntitySchema`    | `ChangeSetWithEntity`    |
| `CitationInstanceCreateIn`     | `CitationInstanceCreate` |
| `CitationInstanceSchema`       | `CitationInstance`       |
| `CitationLinkSchema`           | `CitationLink`           |
| `CitedChangeSetCitationSchema` | `CitedChangeSetCitation` |
| `CitedChangeSetSchema`         | `CitedChangeSet`         |
| `ClaimSchema`                  | `Claim`                  |
| `EditCitationInput`            | `EditCitationInput`      |
| `FieldChangeSchema`            | `FieldChange`            |
| `InlineCitationSchema`         | `InlineCitation`         |
| `RetractionSchema`             | `Retraction`             |
| `RevertNoteSchema`             | `RevertNote`             |
| `ReviewClaimSchema`            | `ReviewClaim`            |
| `ReviewLinkSchema`             | `ReviewLink`             |
| `RichTextSchema`               | `RichText`               |
| `SourceSchema`                 | `CitationSource`         |
| `SourcesPageSchema`            | `SourcesPage`            |
| `UndoChangeSetSchema`          | `UndoChangeSet`          |
| `UndoResultSchema`             | `UndoResult`             |

### `catalog` (71 schemas)

The bulk of the work. Tables grouped by sub-area for readability.

#### Top-level (`apps/catalog/api/schemas.py`)

| Current                     | New                   |
| --------------------------- | --------------------- |
| `AggregatedMediaSchema`     | `AggregatedMedia`     |
| `AlreadyDeletedSchema`      | `AlreadyDeleted`      |
| `BlockingReferrerSchema`    | `BlockingReferrer`    |
| `ClaimPatchSchema`          | `ClaimPatch`          |
| `CreateSchema`              | `EntityCreateInput`   |
| `CreditSchema`              | `Credit`              |
| `CreditInput`               | `CreditInput`         |
| `DeletePreviewBase`         | `DeletePreviewBase`   |
| `DeleteResponseSchema`      | `DeleteResponse`      |
| `EditOptionItem`            | `EditOption`          |
| `GameplayFeatureSchema`     | `GameplayFeatureRef`  |
| `HierarchyClaimPatchSchema` | `HierarchyClaimPatch` |
| `Ref`                       | `Ref`                 |
| `RelatedTitleSchema`        | `RelatedTitle`        |
| `SoftDeleteBlockedSchema`   | `SoftDeleteBlocked`   |
| `TitleRefSchema`            | `TitleRef`            |

(`GameplayFeatureSchema` is `Ref + count`. Renaming to
`GameplayFeatureRef` clarifies that — see the docstring guidance in
[ApiDesign.md](../../../ApiDesign.md) about preserving expansion points.)

#### Titles (`apps/catalog/api/titles.py`)

| Current                     | New                   |
| --------------------------- | --------------------- |
| `AgreedSpecsSchema`         | `AgreedSpecs`         |
| `CrossTitleLinkSchema`      | `CrossTitleLink`      |
| `TitleClaimPatchSchema`     | `TitleClaimPatch`     |
| `TitleDeletePreviewSchema`  | `TitleDeletePreview`  |
| `TitleDeleteResponseSchema` | `TitleDeleteResponse` |
| `TitleDetailSchema`         | `TitleDetail`         |
| `TitleListSchema`           | `TitleListItem`       |
| `TitleMachineSchema`        | `TitleMachine`        |
| `TitleMachineVariantSchema` | `TitleMachineVariant` |

(`TitleListSchema` → `TitleListItem` rather than `TitleList`: it's
the row shape, not a wrapper around a list.)

#### Machine models (`apps/catalog/api/machine_models.py`)

| Current                    | New                    |
| -------------------------- | ---------------------- |
| `MachineModelDetailSchema` | `MachineModelDetail`   |
| `MachineModelGridSchema`   | `MachineModelGridItem` |
| `MachineModelListSchema`   | `MachineModelListItem` |
| `ModelClaimPatchSchema`    | `ModelClaimPatch`      |
| `ModelDeletePreviewSchema` | `ModelDeletePreview`   |
| `ModelEditOptionsSchema`   | `ModelEditOptions`     |
| `ModelRecentSchema`        | `ModelRecent`          |
| `ModelRefSchema`           | `ModelRef`             |
| `VariantSchema`            | `MachineModelVariant`  |

#### People (`apps/catalog/api/people.py`)

| Current                         | New                       |
| ------------------------------- | ------------------------- |
| `PersonSchema`                  | `PersonListItem`          |
| `PersonGridSchema`              | `PersonGridItem`          |
| `PersonDetailSchema`            | `PersonDetail`            |
| `PersonDeletePreviewSchema`     | `PersonDeletePreview`     |
| `PersonSoftDeleteBlockedSchema` | `PersonSoftDeleteBlocked` |
| `PersonTitleSchema`             | `PersonTitle`             |

#### Manufacturers / corporate entities (`apps/catalog/api/manufacturers.py`, `corporate_entities.py`, `locations.py`)

| Current                              | New                                  |
| ------------------------------------ | ------------------------------------ |
| `CorporateEntityClaimPatchSchema`    | `CorporateEntityClaimPatch`          |
| `CorporateEntityDetailSchema`        | `CorporateEntityDetail`              |
| `CorporateEntityListSchema`          | `CorporateEntityListItem`            |
| `CorporateEntityLocationAncestorRef` | `CorporateEntityLocationAncestorRef` |
| `CorporateEntityLocationSchema`      | `CorporateEntityLocation`            |
| `CorporateEntitySchema`              | `ManufacturerCorporateEntity`        |
| `LocationAncestorRef`                | `LocationAncestorRef`                |
| `LocationChildRef`                   | `LocationChildRef`                   |
| `LocationDetailSchema`               | `LocationDetail`                     |
| `LocationManufacturerSchema`         | `LocationManufacturer`               |
| `ManufacturerDetailSchema`           | `ManufacturerDetail`                 |
| `ManufacturerGridSchema`             | `ManufacturerGridItem`               |
| `ManufacturerPersonSchema`           | `ManufacturerPerson`                 |
| `ManufacturerSchema`                 | `ManufacturerListItem`               |
| `SystemSchema`                       | `ManufacturerSystem`                 |

`SystemSchema` and `CorporateEntitySchema` are both renamed to
`Manufacturer*` names following the `<Parent><Child>` pattern
already used for `ManufacturerPerson` and `LocationManufacturer`.
Both are embedded sub-shapes inside `ManufacturerDetail` —
semantically list-items in "the manufacturer's systems/entities
list" — even though `ManufacturerSystem` happens to be exactly
`name + slug` today. Per
[ApiDesign.md](../../../ApiDesign.md), naming a list-item shape
preserves a future expansion point (e.g., adding `model_count`)
that collapsing to `Ref` would foreclose.

`ManufacturerCorporateEntity` is genuinely distinct in shape from
`CorporateEntityListItem` — the embedded form lacks `manufacturer`
and `model_count` since both are context-redundant when nested
under a manufacturer detail. A future consolidation of those two
shapes (if the field divergence isn't load-bearing) is tracked in
[ApiSvelteBoundaryFollowups.md](ApiSvelteBoundaryFollowups.md).

#### Systems (`apps/catalog/api/systems.py`)

| Current              | New              |
| -------------------- | ---------------- |
| `SystemCreateSchema` | `SystemCreate`   |
| `SystemDetailSchema` | `SystemDetail`   |
| `SystemListSchema`   | `SystemListItem` |

(See collision note above.)

#### Series, themes, franchises, gameplay features, taxonomy, reward types, credit roles

| Current                          | New                            |
| -------------------------------- | ------------------------------ |
| `SeriesDetailSchema`             | `SeriesDetail`                 |
| `SeriesListSchema`               | `SeriesListItem`               |
| `ThemeDetailSchema`              | `ThemeDetail`                  |
| `ThemeListSchema`                | `ThemeListItem`                |
| `FranchiseDetailSchema`          | `FranchiseDetail`              |
| `FranchiseListSchema`            | `FranchiseListItem`            |
| `GameplayFeatureDetailSchema`    | `GameplayFeatureDetail`        |
| `GameplayFeatureInput`           | `GameplayFeatureInput`         |
| `GameplayFeatureListSchema`      | `GameplayFeatureListItem`      |
| `TaxonomySchema`                 | `Taxonomy`                     |
| `TaxonomyDeletePreviewSchema`    | `TaxonomyDeletePreview`        |
| `TaxonomyWithTitleCountSchema`   | `TaxonomyWithTitleCount`       |
| `TechnologyGenerationListSchema` | `TechnologyGenerationListItem` |
| `DisplayTypeListSchema`          | `DisplayTypeListItem`          |
| `RewardTypeDetailSchema`         | `RewardTypeDetail`             |
| `CreditRoleDetailSchema`         | `CreditRoleDetail`             |

#### `config/api.py` (top-level)

| Current       | New         |
| ------------- | ----------- |
| `StatsSchema` | `SiteStats` |

## Ghost-type fixes

Settled in this plan; happens as part of the `core` / `config` /
relevant-app commit:

- **`Input` (Ninja-auto-named pagination query model)** — replaced
  with a real Pydantic schema named `PaginationParams` in
  `apps/core/schemas.py` (or wherever pagination is currently
  defined). Endpoints using inline pagination params switch to the
  named model.
- **`JsonBody`** — `apps/core/types.py` defines
  `type JsonBody = dict[str, object]` for test typing. It's leaking
  into OpenAPI through some endpoint declaration. Find and fix the
  call site so `JsonBody` is no longer exposed as an OpenAPI
  component. The Python type alias itself stays.

## Per-app commit sequence

Assumes the _Re-export barrel_ task from
[ApiSvelteBoundary.md](ApiSvelteBoundary.md) has already landed, so
consumers are on named imports from `$lib/api/types` and the ESLint
guardrail blocking `components['schemas']` is active.

Each commit:

1. Renames the app's schema classes per the table above.
2. Updates all backend references (other apps that import the
   schemas, serializers, tests).
3. Runs `make api-gen` to regenerate
   `frontend/src/lib/api/schema.d.ts` and the barrel at
   `frontend/src/lib/api/types.ts` — the barrel updates
   automatically since it's generated from `components['schemas']`
   keys.
4. Codemods consumer named imports: `OldName` → `NewName`
   wherever the renamed types are imported. Identifier-swap diffs
   only; no indexed-access rewrites since the barrel task already
   moved consumers off that pattern.
5. Runs `make lint` and `make test`.

Order, smallest first:

1. **`accounts`** — 4 schemas, low blast radius.
2. **`core`** — 4 schemas. Includes ghost-type cleanup if
   `PaginationParams` lives here.
3. **`config/api.py`** — 1 schema (`StatsSchema` → `SiteStats`).
   Fold into the `core` commit if convenient.
4. **`media`** — 6 schemas. First commit that exercises the
   `…In`/`…Out` → `…Input`/bare migration.
5. **`citation`** — 15 schemas, most defined inline in `api.py`.
6. **`provenance`** — 27 schemas.
7. **`catalog`** — 71 schemas. Largest by far; may split into
   sub-commits per file (titles, machine_models, people,
   manufacturers/locations, systems, series/themes/franchises,
   gameplay features/taxonomy, schemas.py shared) if the diff is
   unwieldy.

## Out of scope

These came up during the audit but belong to other plans or
follow-up work:

- **The `$lib/api/types.ts` re-export barrel.** A pure passthrough
  re-export — never renames. Tracked in [ApiBarrel.md](ApiBarrel.md)
  and summarized as _Re-export barrel_ in
  [ApiSvelteBoundary.md](ApiSvelteBoundary.md).
- **ESLint guardrail banning `components['schemas']` outside
  `client.ts` / `types.ts`.** Tracked alongside the barrel work
  ([ApiBarrel.md](ApiBarrel.md)).
- **Inline schemas defined in endpoint files** (`apps/citation/api.py`
  has 15; `apps/accounts/api.py` has 4; several catalog routers
  define schemas inline rather than in `schemas.py`). This is a
  "where does code live" question, not a naming question. Tracked
  as _Boundary tests_ in
  [ApiSvelteBoundary.md](ApiSvelteBoundary.md).
- **Page-model vs resource-canonical schema split.** The codebase
  currently shares `*Detail` schemas between `/api/<entity>/...`
  and `/api/pages/<entity>/...`. [ApiDesign.md](../../../ApiDesign.md)
  describes them as conceptually distinct; today they aren't.
  Splitting them is an API-design question, not a naming one.
- **Typed error responses across mutating endpoints.** Tracked as
  _Type error responses_ in
  [ApiSvelteBoundary.md](ApiSvelteBoundary.md).
- **Consolidating `ManufacturerCorporateEntity` with
  `CorporateEntityListItem`.** The two shapes diverge only in
  `manufacturer` and `model_count`; whether the divergence is
  load-bearing or the schemas should collapse is tracked in
  [ApiSvelteBoundaryFollowups.md](ApiSvelteBoundaryFollowups.md).
  (`ManufacturerSystem` and `SystemListItem` are kept distinct
  for the same expansion-point reason; no consolidation follow-up.)

## Verification

Per-commit:

- `make lint` clean.
- `make test` passes (backend + frontend).
- `make api-gen` produces a clean `schema.d.ts` diff with only the
  expected renames.
- Spot-check the running app via `make dev` for the area touched.

After all commits land:

- `frontend/src/lib/api/schema.d.ts` contains zero `…Schema`
  component names, zero `…In` / `…Out` component names, no
  generic-name components (`Variant`, `Source`, `Stats`,
  `Recognition`, `Create`, `Input`, `JsonBody`).
- 88 frontend consumers all use the new names.
