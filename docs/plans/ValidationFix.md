# ValidationFix

## Background

Pinbase's catalog truth is claims-based: sources and users assert Claims, claim resolution picks winners, and resolved/model tables materialize the current catalog state. That architecture is sound in principle, but provenance, ingest, end user editing, admin editing, and validation were not designed together from the beginning. Validation was added later and ended up spread across multiple write paths instead of being designed into the system from the start.

Today, "validation" means several different things:

- request validation in user-facing edit APIs
- admin form validation
- ingest-specific source parsing and prechecks
- resolver guard rails and coercion
- post-hoc catalog audit via `validate_catalog`

All of those are useful, but they are not the same thing. The result is that correctness depends on _how_ data enters the system.

## Analysis

See [WritePathMatrix.md](WritePathMatrix.md) for the full inventory. The important findings are:

### 1. There is not one write path today

The current system has several distinct truth-affecting write paths:

- user-facing PATCH claim APIs
- Django admin via `ProvenanceSaveMixin`
- direct admin bypasses
- ingest bulk claim writes
- ingest direct ORM writes
- one-off management command claim writers
- resolution/materialization itself

There is no single place where "all data enters the system."

### 2. User-edit validation is the strongest path

The PATCH path validates:

- scalar field validators
- markdown cross-reference rules
- FK/slug existence
- relationship target existence
- cycle/self-reference checks for some graph relationships
- duplicate checks for submitted relationship payloads

This is the most complete validation logic in the codebase today.

### 3. Bulk ingest claim writes were under-validated (now fixed)

`bulk_assert_claims()` originally validated almost nothing beyond mojibake on string values. Component B added `validate_claims_batch()` which now enforces at the claim boundary:

- ✓ type coercion and field range validators
- ✓ mojibake checks (subsumed from the old step-0 check)
- ✓ markdown cross-reference validation
- ✓ FK target existence (batched, one query per field group)
- relationship target existence (deferred — resolver logs warnings)
- cycle detection (remains a PATCH-only check)

### 4. Some writes still bypass claims entirely

WritePathMatrix identifies direct ORM writes with no claim at all, including:

- direct M2M writes such as `series.titles.add(*titles)`
- direct `save(update_fields=[...])` writes in ingest
- direct `QuerySet.update()` writes
- fields hidden behind `claims_exempt`

These are not just validation gaps. They are provenance coverage gaps.

### 5. Admin is mixed, not cleanly claims-driven

Admin is not one thing:

- `ProvenanceSaveMixin` routes changed scalar fields through claims, but only after the model row is first written
- some admin screens bypass the provenance path entirely
- some relationships remain directly editable rather than claim-controlled

"The admin validates it" is not the same thing as "it went through the claims system." More importantly, trying to make admin behave exactly like the claims UI/API would add complexity to the plan for relatively little value. If admin remains a full catalog edit surface, the system still has a fundamentally different human write path.

### 6. Resolver and audit are carrying too much burden

The resolver is appropriately defensive in some cases, but it should not have to compensate for inconsistent upstream validation. Likewise, `validate_catalog` is useful as a post-hoc quality layer, but it should not be the first place correctness issues are discovered for claim-managed truth.

## Diagnosis

The system's biggest design problem is that the claims architecture is only partially being used as intended. The analysis points to two distinct problems:

**Coverage gaps** — some catalog facts enter the system without a claim, meaning no audit trail, no conflict-resolution mechanism, and no shared claim-boundary validation. These are mechanical correctness gaps in how the current architecture is used.

**Validation gaps** — even when data does go through claims, not all claim write paths validate the same rules. Bulk ingest validates almost nothing beyond mojibake; the interactive PATCH path validates everything. These are semantic consistency gaps at the claim boundary.

The two problems are related, but they do **not** require the same solution. Until coverage gaps are fixed, any attempt to centralise validation will be centralising it at a boundary that not all writes even reach.

The codebase already has everything needed to fix both: an unsaved `Claim` object that carries almost all the data needed for claim-boundary validation; concrete write helpers (`assert_claim()`, `bulk_assert_claims()`, `execute_claims()`); and strong validation logic in `validate_scalar_fields()` in the interactive PATCH path. The right fix is to close the coverage gaps first, then reuse the existing validation logic at the claim boundary. No new service abstractions are needed.

There is also an explicit product decision that simplifies the plan:

- the Django admin does **not** need to remain a catalog edit surface
- catalog models will be unregistered from admin entirely

That means admin does not need to be normalized into the same edit architecture as the claims UI/API. It is reduced to infrastructure/configuration and provenance inspection only. This is the cleanest way to eliminate the strangest human write path in the system.

Finally, there is an operational decision that also simplifies the migration:

- it is acceptable to delete the database and reset migrations back to `0001`

That removes a large class of migration/backfill complexity. The plan can optimize for achieving a coherent architecture in the codebase rather than preserving every historical intermediate state in-place.

## Remove Admin as a Catalog-Truth Writer ✓

All 20 catalog models are unregistered from Django admin. `catalog/admin.py` contains only a docstring explaining the rationale. A test (`TestCatalogModelsNotInAdmin`) enforces this — any future registration will fail CI.

`ProvenanceSaveMixin` has been removed from the codebase entirely.

Admin remains registered for:

- `Source` (write — managing ingest sources)
- `ChangeSet` (write — grouping user edits)
- `Claim` (read-only inspection — `has_add/change/delete_permission` all return `False`, enforced by `TestClaimAdminIsReadOnly`)
- `License` (write — content licensing configuration)
- `User` (write — account management)

## Component A — Fix Coverage Gaps First

Make every intended catalog fact go through claims. This is mechanical work and should be done before extracting new abstractions.

### A1. Remove non-justified `claims_exempt` declarations ✓

Every `claims_exempt` declaration on every model was reviewed. The architectural rule is: every field set by a human or data source requires a claim. The only legitimate exemptions are fields set exclusively by the database engine: `id`/`uuid`, `created_at`, `updated_at`.

All per-model exemptions have been removed and claim assertions added:

| Model                     | Fields migrated                                                   |
| ------------------------- | ----------------------------------------------------------------- |
| `Person`                  | `wikidata_id`                                                     |
| `Manufacturer`            | `wikidata_id`, `opdb_manufacturer_id`                             |
| `CorporateEntity`         | `manufacturer`, `ipdb_manufacturer_id`                            |
| `Title`                   | `opdb_id`, `fandom_page_id`, `needs_review`, `needs_review_notes` |
| `TechnologySubgeneration` | `technology_generation` (parent FK)                               |
| `DisplaySubtype`          | `display_type` (parent FK)                                        |
| `System`                  | `manufacturer`, `technology_subgeneration`                        |

`Location.location_path` is exempt and correctly so — it is a computed hierarchical path derived from the location hierarchy, not an editorially asserted value.

WritePathMatrix is the authoritative field inventory for this work.

**Resolver prerequisite: `preserve_when_unclaimed`.** The resolver resets all claim-controlled fields to defaults before applying winners. For UNIQUE fields and non-nullable FKs, the default is invalid (shared `""` causes IntegrityError or FK descriptor crash). The resolver already preserved UNIQUE fields, but the logic was named `unique_attrs` — hiding the invariant. This was renamed to `preserve_when_unclaimed` and widened to also cover non-nullable FK fields (`field.many_to_one and not field.null`). `get_field_defaults()` was also fixed to return `None` (not `""`) for FK fields, since Django's FK descriptor rejects `""` on assignment. Without this fix, resolving a `TechnologySubgeneration` via API PATCH (or in tests) without a `technology_generation` claim would crash.

**The global exemption list in `core/models.py`.** ✓

`slug` has been removed from `_CLAIMS_EXEMPT_NAMES`. `extra_data` remains legitimately exempt (it is the resolver's output bag, not an asserted fact).

**What was done:**

1. Removed `slug` from `_CLAIMS_EXEMPT_NAMES` so the resolver discovers and materialises slug claims.
2. Added `resolve_unique_conflicts()` — a generalised conflict detection function in `_helpers.py` that handles both nullable unique fields (clear loser to None, e.g. `opdb_id`) and non-nullable unique fields (revert loser to pre-resolution value with preserver-wins semantics, e.g. `slug`). Replaces the old `_resolve_opdb_conflicts()`.
3. Added `get_preserve_fields()` — a shared utility in `_helpers.py` that identifies UNIQUE and non-nullable FK fields. Replaces four inline copies of the same predicate.
4. Fixed `_apply_resolution()` (MachineModel path) to use `preserve_when_unclaimed` logic, matching `_resolve_bulk` and `_resolve_single`.
5. Asserted slug claims in all ingest commands for entities each source creates. Sources only assert slug claims for entities they create — not for pre-existing entities they reference (unlike scalar claims like name/year, no external source has a slug opinion).
6. Direct slug writes (bootstrap `bulk_create_validated`, Title slug renames via `QuerySet.update`) remain as A4 bootstrap writes — the slug claim is asserted in the same pass.

**Source attribution rule for slug claims.** Sources only assert slug claims for entities they create — never for pre-existing entities they reference. This differs from scalar claims (name, year) where confirming a pre-existing value is useful provenance ("IPDB agrees the year is 1997"). No external source provides slug data, so asserting a slug claim for a pre-existing entity would attribute a decision that source never made. When a user edits an entity via the claims UI, they DO assert a slug claim — they are the source of that slug choice.

**Remaining:** Remove auto-slug generation from catalog model `save()` methods (17 models). Currently save() auto-generates a slug if blank — this is a safety net that is no longer needed now that all ingest paths supply slugs explicitly. Removing it enforces the invariant that slugs come from exactly two sources: ingest and user edit. This also requires fixing ~173 tests that create objects without providing a slug.

### A2. Replace direct ORM writes to claim-controlled data — subsumed ✓

All direct ORM writes now have corresponding claim assertions in the same ingest pass (A4 bootstrap pattern). Slug writes (bootstrap `bulk_create_validated`, Title slug renames via `QuerySet.update`) are included. No separate A2 step was needed.

### A3. Bring remaining editorial relationships under claims ✓

The known case was `series.titles.add(*titles)` in `ingest_pinbase`, which wrote series-title membership directly as a M2M operation with no claim. This has been replaced with claims-based membership.

**What was done:**

1. Added `"series_title": {"title_slug": "title"}` to `RELATIONSHIP_SCHEMAS` in `claims.py`.

2. Replaced `series.titles.add()` with `bulk_assert_claims()` calls using `sweep_field="series_title"` and an authoritative scope covering all series in the DB, so titles removed from a series are retracted on subsequent runs.

3. Added a standalone `resolve_all_series_titles()` in `resolve/_relationships.py` that resolves `series_title` claims into `Series.titles` through-table rows using a single query and a diff/apply approach. It was written as a standalone function rather than using `_resolve_machine_model_m2m()` because the claim lives on `Series`, not `MachineModel` — parameterising the generic helper would have added complexity for a single non-MachineModel use case.

4. As part of this work, `_resolve_all_m2m()` was renamed to `_resolve_machine_model_m2m()` to make explicit that the generic helper is scoped to MachineModel relationships only.

If WritePathMatrix identifies further direct M2M writes for editorial relationships, apply the same treatment using the standalone resolver pattern.

### Implementation pitfalls for A1–A3 (resolved)

Two bug classes emerged during A3 implementation. Both have been structurally fixed during A1 work.

**Wrong content type.** Every `Claim` object must be created with the content type for the model that _owns_ the claim, not the model being iterated. When a single ingest method touches multiple model types (e.g. `_ingest_titles` creates claims on both `Title` and `Series`), each model needs its own `ct_id` captured separately. Reusing `ct_id` across model types produces claims attached to the wrong object silently — no error, wrong data.

The structural fix is `Claim.for_object()` — a classmethod that derives the content type from the object itself, eliminating the `ct_id` variable and the footgun entirely:

```python
# Before
ct_id = ContentType.objects.get_for_model(Series).pk
Claim(content_type_id=ct_id, object_id=series.pk, field_name=..., value=...)

# After
Claim.for_object(series, field_name=..., value=...)
```

`ContentType.objects.get_for_model()` is cached by Django after the first call per model type, so there is no performance concern inside loops. The call-site form also reads more naturally — "a claim about this series" rather than "a claim with this content type ID and this object ID."

`Claim.for_object()` has been applied to all claim construction sites in files touched during A1. Remaining files still use the old `Claim(content_type_id=ct_id, ...)` pattern — migrate opportunistically when those files are touched for other work.

**Claims built against unstable identity values.** When a claim value references another object's slug (or any identity value that might change later in the same ingest pass), the claim must use the effective post-operation value, not the pre-operation value. In `_ingest_titles`, series-title claims were initially built using `title.slug` before the slug rename loop ran, producing claims that referenced a slug that no longer existed in the DB after the rename.

The structural fix for `_ingest_titles` is a **two-pass refactor**: split the method into a collect phase (gather `(title, entry)` pairs, pending slug renames, pending fandom updates, series memberships) followed by the rename/transform phase, then an assert phase that builds all claims using stable post-rename slugs. This eliminates the need for the `pending_slugs.get(title.pk, title.slug)` workaround and makes the phase dependency explicit. The cost is low — the intermediate state is a list of `(title, entry)` pairs.

This two-pass refactor was completed as part of A1 when `_ingest_titles` was modified to add claim assertions for `fandom_page_id` and `opdb_id`. The method is now wrapped in `transaction.atomic()` for phase-level atomicity.

The broader principle: **claims that reference another object's identity must be built after all identity updates in the same pass have been applied.**

### A4. Document acceptable bootstrap writes

Some ingest commands write fields directly before asserting claims for those same fields in the same pass — for example, `MachineModel.objects.bulk_update([...], ["opdb_id", "ipdb_id"])` in `ingest_pinbase` and `ingest_opdb`, followed immediately by `bulk_assert_claims()` for the same values. This pattern is acceptable: the bootstrap write and the claim assertion travel together in the same ingest run, so the claim always catches up.

No change is required for these writes. Inline comments documenting the bootstrap write dependency have not been added yet — this is a documentation-only task.

## Component B — Reuse Existing Validation Logic at the Claim Boundary

Once writes actually reach the claim boundary, add shared validation there by extracting and reusing the logic that already exists in the interactive edit path. This includes one-off management command claim writers: they already route through `assert_claim()` or `bulk_assert_claims()` (so they have no coverage gap), but they currently get no more validation than any other bulk caller. Component B closes that gap for `bulk_assert_claims()` callers automatically. Single-claim writers that use `assert_claim()` directly (such as `scrape_images`) are a smaller surface but should also be audited and wired to `validate_claim_value()` once it exists.

### B1. Extract `validate_claim_value()` ✓

The scalar/direct-field validation from `validate_scalar_fields()` was extracted into `provenance/validation.py`:

```python
def validate_claim_value(field_name: str, value, model_class) -> Any:
    """Validate and possibly transform a scalar claim value.
    Raises ValidationError on failure."""
```

This covers, for direct-field claims:

- type coercion via `field.to_python()`
- Django field validator chain (range, URL format, etc.)
- mojibake checks
- markdown cross-reference validation (authoring → storage format conversion)

`validate_scalar_fields()` in `edit_claims.py` now delegates to `validate_claim_value()`, keeping request-level concerns (unknown field rejection, null/blank clearability) in the API layer while the per-value validation is shared.

### B2. Call it from `bulk_assert_claims()` ✓

`bulk_assert_claims()` now calls `validate_claims_batch()` before persisting claims. This function uses `classify_claim()` — a structural classifier in `provenance/validation.py` that derives claim type from data already on the claim, with no catalog-specific imports:

- **DIRECT** — `field_name` in `get_claim_fields(model_class)` → scalar validation or FK batch check
- **RELATIONSHIP** — compound `claim_key` + dict value with `exists` key → pass through
- **EXTRA** — unrecognized field on a model with a concrete `extra_data` JSONField → pass through
- **UNRECOGNIZED** — none of the above → reject with warning

The classifier is tested exhaustively: a contract test iterates every namespace in `RELATIONSHIP_SCHEMAS` and proves that `build_relationship_claim()` output classifies as `RELATIONSHIP`. Boundary tests verify that unknown fields on models with `extra_data` classify as `EXTRA` while unknown fields on models without `extra_data` classify as `UNRECOGNIZED`.

Batch mode logs and skips invalid claims rather than failing the entire ingest. `bulk_assert_claims()` returns a `validation_rejected` count in its stats dict.

**JSON→Django type boundary.** Claim values are stored in a JSONField, which has no Decimal type — numeric values arrive as Python floats. `DecimalField.to_python(float)` produces IEEE 754 artifacts (e.g. `8.95` → `Decimal('8.950')`) that `DecimalValidator` rejects for exceeding `decimal_places`. The fix is to stringify floats before `to_python` so the string path produces clean Decimals: `to_python("8.95")` → `Decimal("8.95")`. This is a general concern at the JSON→Django type boundary, not a Decimal special case.

### B3. Batched FK target validation ✓

FK claims are validated in batch by `validate_fk_claims_batch()`:

- groups claims by `(model_class, field_name)` — one query per group
- uses the `claim_fk_lookups` convention from the resolver to determine the lookup key
- rejects claims referencing non-existent targets

**Relationship target validation is deferred.** Relationship claims are now structurally identifiable via `classify_claim()` without catalog imports. Extending B3 to validate their target slugs would require a registry mapping relationship namespace + slug key to target model. The resolver already logs warnings for unmatched relationship slugs. This is a follow-up, not a prerequisite.

### B4. Validate `assert_claim()` callers ✓

`assert_claim()` now calls `classify_claim()` and `validate_claim_value()` for DIRECT claims, and rejects UNRECOGNIZED claims with `ValueError`. This closes the gap for callers like `scrape_images` that lack upstream validation. The PATCH path double-validates (upstream in `validate_scalar_fields`, again in `assert_claim`) — harmless for single-claim writes.

Resolver tests that previously persisted invalid data to test defensive coercion (`test_invalid_int_coercion`, `test_malformed_int_claim_uses_default`) now verify that `assert_claim` rejects the invalid value at the boundary. This confirms the resolver's defensive coercions for bad scalar data are no longer reachable through any write path.

### Implementation notes

**Ingest tests need FK target rows.** FK validation at the claim boundary means ingest integration tests must seed taxonomy rows (TechnologyGeneration, DisplayType, etc.) that their FK claims reference. An `ingest_taxonomy` fixture was added to the catalog test conftest for this. Previously these claims were persisted without the FK targets existing — the resolver handled missing targets gracefully, but the data quality issue was invisible until resolution time.

## Enforcement Modes ✓

User edits and ingest are not treated as identical operational flows. The system enforces the same semantic rules in different modes:

### Interactive mode

For user-facing edits and similar synchronous writes (`validate_scalar_fields` → `execute_claims`):

- fail fast on the first invalid field
- return explicit `HttpError 422` errors
- block the write

### Batch ingest mode

For ingest (`validate_claims_batch` inside `bulk_assert_claims`):

- batch/prefetch lookups (one query per FK field group)
- log and skip invalid claims
- continue processing valid claims
- return `validation_rejected` count in stats

## Migration Order

1. ✓ **Use WritePathMatrix as the source inventory.**
   Enumerate and confirm every remaining bypass and every field/relationship that still fails to go through claims.

2. ✓ **Remove admin as a catalog-truth writer.**
   All catalog models unregistered, `ProvenanceSaveMixin` removed, test enforcement in place.

3. ✓ **Fix Component A.**
   Remove non-justified `claims_exempt`, migrate direct writes, and bring claim-managed facts onto claims. Slug removed from `_CLAIMS_EXEMPT_NAMES`, slug claims asserted in all ingest commands, conflict detection generalised. Remaining: remove auto-slug from 17 catalog model `save()` methods + fix ~173 tests.

4. ✓ **Fix Component B: scalar and FK validation at the claim boundary.**
   `validate_claim_value()` extracted, called from `bulk_assert_claims()`, batched FK target checks added.

5. ✓ **Validate `assert_claim()` callers** (B4).
   `assert_claim()` now validates DIRECT claims and rejects UNRECOGNIZED claims via `classify_claim()`.

6. **Extend B3 to relationship target validation** (optional).
   Batch-validate slug references inside relationship claim dicts. `classify_claim()` now identifies relationship claims structurally — a registry mapping namespace + slug key to target model is the remaining piece. Deferred because the resolver already logs warnings for unmatched targets.

7. **Trim `validate_catalog` and review resolver guard rails.**
   Review the resolver's defensive coercions — upstream validation now ensures only valid values reach claims through both `bulk_assert_claims` and `assert_claim`. Evidence: resolver tests for invalid-data coercion (`test_invalid_int_coercion`, `test_malformed_int_claim_uses_default`) now verify rejection at the claim boundary instead, confirming those resolver code paths are unreachable.

   `validate_catalog` checks fall into three categories after Component B:

   **Genuinely post-resolution** (keep):
   `check_golden_records` (end-to-end regression), `check_self_referential_variant`, `check_variant_chains` (structural invariants), `check_orphan_claims`, `check_unresolved_fk_claims`, `check_unresolved_credit_claims`, `check_unresolved_m2m_claims`, `check_credits_without_matching_claims` (referential integrity after resolution)

   **Potentially redundant with claim boundary** (review):
   `check_nameless_models`, `check_nameless_titles`, `check_nameless_persons` — these check for empty names after resolution. The claim boundary validates name _values_ but does not enforce that a name claim _exists_. These remain useful as resolution-outcome checks until we enforce required-claim coverage.

   **Info/data quality only** (keep as-is):
   `check_summary_stats`, `check_duplicate_persons`, `check_duplicate_manufacturers`, `check_models_without_corporate_entity`, `check_models_without_year`, `check_titles_needing_review`, `check_uncurated_themes`

8. **Only after that, decide whether new abstractions are warranted.**

## Follow-ups Out of Scope for This Plan

### Slug editing UI

After A1 slug migration, the backend fully supports slug claims: `get_claim_fields()` returns `slug`, `execute_claims()` can process slug claims via PATCH, and the resolver materializes and conflict-checks them. Ingest slugs are fully claim-controlled with source attribution.

What remains is the frontend UX: a propose/approve flow where the UI auto-generates a slug proposal from the name, the user can see, modify, and approve it, and it is submitted as a claim. This also applies to entity creation — the user needs to see and confirm the slug before the record is created. This is a UX feature that builds on the backend infrastructure but is separate from the coverage-gap work in this plan.

### Taxonomy edit UIs

All taxonomy/vocabulary models (TechnologyGeneration, TechnologySubgeneration, DisplayType, DisplaySubtype, Cabinet, GameFormat, CreditRole, Franchise, RewardType, Tag, Theme, GameplayFeature) are currently fully ingest-managed from pindata JSON. Removing admin write access is safe today.

However, these models will need user-facing edit UIs. Taxonomy values are editorial decisions — adding a new technology generation, renaming a credit role, or reorganising display subtypes should go through the same claims-based edit path as other catalog truth, not require a pindata JSON edit and re-ingest.

This is a separate feature project, not a prerequisite for this plan.

## Acceptance Criteria

This plan is successful when:

- all intended catalog facts flow through claims
- ✓ catalog models are unregistered from Django admin
- remaining direct writes are either removed or explicitly documented as true bootstrap exceptions
- ✓ `bulk_assert_claims()` and `assert_claim()` validate direct-field claim values using shared logic extracted from the interactive edit path
- ✓ FK existence checks run at claim-write time in ingest using batched lookups
- ✓ provenance layer has no architectural imports from catalog (structural `classify_claim()` replaces `RELATIONSHIP_NAMESPACES` import)
- relationship target existence checks run at claim-write time (deferred — resolver logs warnings for now)
- editorial relationships identified in WritePathMatrix are materialised from claims, not written directly
- `validate_catalog` no longer carries correctness rules that should have been enforced upstream
- resolver defensive guard rails that compensate for upstream validation gaps have been reviewed and trimmed
- the codebase can be recreated cleanly from a reset initial migration set
