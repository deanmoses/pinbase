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

## Remove Admin as a Catalog-Truth Writer

Catalog models should be unregistered from Django admin entirely. Read-only admin requires overriding `has_add_permission`, `has_change_permission`, and `has_delete_permission` on every `ModelAdmin` and maintaining that discipline for every new model added — it is boilerplate that leaks. Unregistering is enforced by absence with nothing to misconfigure.

Admin remains registered for:

- `Source`
- provenance inspection (`Claim`, `ChangeSet`)
- internal infrastructure/configuration models

This eliminates the strangest human write path in the system without introducing new maintenance surface.

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

**The global exemption list in `core/models.py`.**

`get_claim_fields()` uses a global `_CLAIMS_EXEMPT_NAMES` set that excludes `slug` and `extra_data` from claim discovery on every model. `extra_data` is legitimately exempt — it is the resolver's output bag, not an asserted fact. `slug` is not legitimately exempt.

`slug` must be removed from `_CLAIMS_EXEMPT_NAMES`. The intended behaviour: when a user enters a name in the edit UI, the system proposes a slug which the user can modify and approve. The approved slug becomes a claim. Ingest commands also assert slug claims. The resolver materialises the winning slug claim onto the model row, with conflict handling matching the existing `opdb_id` pattern.

This requires:

1. Remove `slug` from `_CLAIMS_EXEMPT_NAMES` so the resolver discovers and materialises slug claims.
2. Add slug resolution and conflict handling to the resolver (a slug claimed by one object cannot be applied to another).
3. Assert slug claims in all ingest commands that currently write slugs directly.
4. Replace direct slug writes (`QuerySet.update()` for renames, slug assignments at creation time) with claim assertions — this is the remaining A2 work.
5. The edit UI propose/approve flow for slug management is a separate feature — see Follow-ups.

**Test impact warning.** Slug is UNIQUE, so `preserve_when_unclaimed` will prevent the resolver from crashing on objects without a slug claim. But every test that creates an object also creates a slug — and once slug is claim-controlled, any resolution triggered by a PATCH or `resolve_all_entities` will preserve the existing slug only as long as no _other_ object's slug claim conflicts with it. More importantly, the slug migration will touch every ingest command and every model, making it the widest A1-style change. Consider a test fixture or helper that creates an object with its corresponding slug claim, to avoid updating dozens of tests individually.

### A2. Replace direct ORM writes to claim-controlled data — subsumed

A1 added claim assertions alongside existing direct writes. Those direct writes are now bootstrap writes covered by A4 (the claim and the direct write travel together in the same ingest pass). The remaining direct writes that lack claims are all slug-related (`QuerySet.update()` for slug renames in `_ingest_titles`, slug assignments at `bulk_create_validated` time). These are blocked on the slug migration — they will be addressed when `slug` is removed from `_CLAIMS_EXEMPT_NAMES`.

No separate A2 step is needed.

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

No change is required for these writes. Add an inline comment making the dependency explicit, so future maintainers do not break the pairing.

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

`bulk_assert_claims()` now calls `validate_claims_batch()` before persisting claims. This function classifies each claim by `field_name` and applies the appropriate validation:

1. **Relationship namespace** — in `RELATIONSHIP_NAMESPACES` → pass through
2. **Scalar claim field** — in `get_claim_fields` and not a relation → validate via `validate_claim_value()`
3. **FK claim field** — in `get_claim_fields` and is a relation → batch FK target check
4. **Extra-data** — not in claim fields, but model has `extra_data` → pass through
5. **Unrecognized** — not in claim fields, no `extra_data` fallback → reject

Batch mode logs and skips invalid claims rather than failing the entire ingest. `bulk_assert_claims()` returns a `validation_rejected` count in its stats dict.

**`extra_data` classification.** Claims whose `field_name` is not in `get_claim_fields()` are not necessarily invalid. Models with an `extra_data` JSONField accept arbitrary claim field names — the resolver dumps unrecognized winners into `extra_data`. This includes dotted namespaces like `wikidata.description` and undotted names like `manufacturer` on MachineModel (where it is not a concrete field). Only models _without_ `extra_data` reject unrecognized field names.

**JSON→Django type boundary.** Claim values are stored in a JSONField, which has no Decimal type — numeric values arrive as Python floats. `DecimalField.to_python(float)` produces IEEE 754 artifacts (e.g. `8.95` → `Decimal('8.950')`) that `DecimalValidator` rejects for exceeding `decimal_places`. The fix is to stringify floats before `to_python` so the string path produces clean Decimals: `to_python("8.95")` → `Decimal("8.95")`. This is a general concern at the JSON→Django type boundary, not a Decimal special case.

### B3. Batched FK target validation ✓

FK claims are validated in batch by `validate_fk_claims_batch()`:

- groups claims by `(model_class, field_name)` — one query per group
- uses the `claim_fk_lookups` convention from the resolver to determine the lookup key
- rejects claims referencing non-existent targets

**Relationship target validation is deferred.** Relationship claims (credit, theme, tag, etc.) have dict values whose slug-key-to-target-model mapping is catalog-layer domain knowledge in `RELATIONSHIP_SCHEMAS`. The resolver already logs warnings for unmatched relationship slugs. Extending B3 to cover relationship targets would require passing the schema mapping into the provenance layer or adding a registry — that is a follow-up.

### B4. Audit `assert_claim()` callers

`assert_claim()` (the single-claim writer) has no validation. The PATCH path validates upstream before calling `execute_claims()` → `assert_claim()`, so interactive edits are covered. But `scrape_images` calls `assert_claim()` directly with no upstream validation. This should be audited and wired to `validate_claim_value()`.

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

2. **Remove admin as a catalog-truth writer.**
   Unregister catalog models from admin. Keep admin only for infrastructure/configuration and provenance inspection.

3. ✓ (slug remaining) **Fix Component A.**
   Remove non-justified `claims_exempt`, migrate direct writes, and bring claim-managed facts onto claims. Slug migration is in progress separately.

4. ✓ **Fix Component B: scalar and FK validation at the claim boundary.**
   `validate_claim_value()` extracted, called from `bulk_assert_claims()`, batched FK target checks added.

5. **Audit `assert_claim()` callers** (B4).
   Wire `validate_claim_value()` into `assert_claim()` for callers like `scrape_images` that lack upstream validation.

6. **Extend B3 to relationship target validation** (optional).
   Batch-validate slug references inside relationship claim dicts. Deferred because the resolver already logs warnings for unmatched targets.

7. **Trim `validate_catalog` and review resolver guard rails.**
   Remove correctness checks from `validate_catalog` that are now guaranteed upstream. Review the resolver's defensive coercions — once upstream validation ensures only valid values reach claims, the resolver should not need to compensate for invalid data.

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
- catalog models are unregistered from Django admin
- remaining direct writes are either removed or explicitly documented as true bootstrap exceptions
- ✓ `bulk_assert_claims()` validates direct-field claim values using shared logic extracted from the interactive edit path
- ✓ FK existence checks run at claim-write time in ingest using batched lookups
- relationship target existence checks run at claim-write time (deferred — resolver logs warnings for now)
- editorial relationships identified in WritePathMatrix are materialised from claims, not written directly
- `validate_catalog` no longer carries correctness rules that should have been enforced upstream
- resolver defensive guard rails that compensate for upstream validation gaps have been reviewed and trimmed
- the codebase can be recreated cleanly from a reset initial migration set
