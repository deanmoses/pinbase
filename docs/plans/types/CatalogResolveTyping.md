# Step 10.3: `catalog/resolve/*` typing pass

Detailed plan for [Step 10.3 of MypyFixing.md](MypyFixing.md). Steps 10.1 and 10.2 (behavior fixes) land first and are tracked in MypyFixing.md, not here.

## Context

45 baseline mypy entries in `backend/apps/catalog/resolve/*.py`. The user's stated goal is **not** just burning down entries — it's defining the types _up front_ before wiring, to avoid the reverse-engineering pattern from the catalog-app refactor.

The 45 errors cluster into four root causes:

1. **`_annotate_priority(qs)` is untyped** — ~9 `no-untyped-call` errors across every resolver.
2. **`claim.value` is `object`** (JSONField payload) and is accessed with string keys across ~10 resolvers. Shape knowledge is implicit at every call site.
3. **Tuple-shape variable reuse** in [\_relationships.py](../../../backend/apps/catalog/resolve/_relationships.py) and [\_media.py](../../../backend/apps/catalog/resolve/_media.py): loop variables get assigned from `values_list(...)` tuples of different arities (or a tuple and a model instance) in the same scope, tripping `Incompatible types in assignment` + `Need more than N values to unpack`.
4. **Untyped keystone helpers** — `validate_check_constraints`, `_coerce`, `_resolve_fk_generic`, `_sync_markdown_references`, `_resolve_aliases`, `_resolve_parents`, `resolve_entity`, `resolve_all_entities` all missing annotations.

[\_media.py](../../../backend/apps/catalog/resolve/_media.py) is already the cleanest file — 5 NamedTuples in place — and serves as the shape target for the rest.

## Scope — behavior-preserving

Pure typing cleanup. No resolver logic changes. The only baseline movement is downward.

## Prerequisites

[ProvenanceValidationTightening.md](ProvenanceValidationTightening.md) (Step 10.2) lands first. This plan's TypedDicts mirror the registry schemas 10.2 establishes — required/optional/type per value_key must match. Serializing the two steps means the contract is settled at implementation time, not guessed at design time.

The TypedDicts mark `exists` and FK keys as Required — that's the post-10.2 wire contract. 10.3's Phase B still reads with `cast + .get()` (not subscript) to keep the runtime-adjacent subscript flip out of this large typing diff — Step 10.4 ([ResolverReadsTightening.md](ResolverReadsTightening.md)) is a focused follow-up that does the flip in isolation.

## Approach

### Phase A — Define the claim-value vocabulary up front

New module `backend/apps/catalog/resolve/_claim_values.py` with **7 TypedDicts**, one per distinct JSON payload shape. No wiring yet — lands in isolation so the vocabulary is reviewable on its own.

| TypedDict                   | Used by                                                              | Required                                   | `NotRequired`                               |
| --------------------------- | -------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------- |
| `GameplayFeatureClaimValue` | `resolve_all_gameplay_features`                                      | `gameplay_feature: int`, `exists: bool`    | `count: int \| None`                        |
| `CreditClaimValue`          | `resolve_all_credits`                                                | `person: int`, `role: int`, `exists: bool` | —                                           |
| `AbbreviationClaimValue`    | `resolve_all_title_abbreviations`, `resolve_all_model_abbreviations` | `value: str`, `exists: bool`               | —                                           |
| `AliasClaimValue`           | `_resolve_aliases` (6 alias resolvers)                               | `alias_value: str`, `exists: bool`         | `alias_display: str`                        |
| `ParentClaimValue`          | `_resolve_parents`                                                   | `parent: int`, `exists: bool`              | —                                           |
| `MediaAttachmentClaimValue` | `resolve_media_attachments`                                          | `media_asset: int`, `exists: bool`         | `category: str \| None`, `is_primary: bool` |
| `LocationClaimValue`        | `resolve_all_corporate_entity_locations`                             | `location: int`, `exists: bool`            | —                                           |

**`exists` is Required on all 7 TypedDicts.** Post-10.2, [classify_claim](../../../backend/apps/provenance/validation.py#L86) + the shared relationship validator guarantee every relationship-claim row has `exists: bool`.

**`LocationClaimValue` is a relationship claim, not DIRECT.** `CorporateEntity` at [manufacturer.py:129](../../../backend/apps/catalog/models/manufacturer.py#L129) has no `location` column; the payload materializes `CorporateEntityLocation` rows. 10.1 adds the `exists=False` retraction handling; the TypedDict models the post-10.1 wire shape.

**No `M2MClaimValue` TypedDict.** The generic resolver [\_resolve_machine_model_m2m](../../../backend/apps/catalog/resolve/_relationships.py#L86) reads the payload with a runtime key (`val[spec.field_name]`), which TypedDict can't express. Use `Mapping[str, object]` + `type(target_pk) is int` narrowing in that one helper. The field-specific TypedDicts above cover the non-generic relationship resolvers.

**Placement** — `resolve/_claim_values.py` for now. These are read-side only. If a future step types the claim _builders_ in `apps.catalog.claims`, moving the types to `apps.catalog.claims.types` is a rename. (10.2's registry additions for literal schemas live separately from these TypedDicts — the registry is write-side metadata; these are read-side shape names.)

**Done when:** `_claim_values.py` exists, mypy + tests pass, no baseline delta.

### Phase B — Wire resolvers to their TypedDicts

Per-resolver-family commits in this order (smallest blast radius first):

1. `_media.py` — `resolve_media_attachments` → `MediaAttachmentClaimValue`.
2. `_relationships.py` simple-M2M family — `resolve_all_themes` / `_tags` / `_reward_types` share the generic `_resolve_machine_model_m2m` helper. No TypedDict here; use `val: Mapping[str, object]` + `type(target_pk) is int` narrowing. `resolve_all_gameplay_features` → `GameplayFeatureClaimValue`.
3. `_relationships.py` credits — `resolve_all_credits` → `CreditClaimValue`.
4. `_relationships.py` abbreviations — both resolvers → `AbbreviationClaimValue`.
5. `_relationships.py` aliases + parents — `_resolve_aliases` → `AliasClaimValue`, `_resolve_parents` → `ParentClaimValue`.
6. `_relationships.py` CE locations — `resolve_all_corporate_entity_locations` → `LocationClaimValue`.

**`cast` names the shape; keep every `.get()`.** Defensive reads for required keys stay in place — the write-path validator won't guarantee them until 10.2 lands, and flipping `.get("person")` to `val["person"]` would turn a legacy malformed row into a KeyError mid-bulk-resolve. `cast` is documentation-only for now; Step 10.4 of MypyFixing.md does the subscript flip once 10.2's runtime guarantees are in place.

```python
val = cast(CreditClaimValue, claim.value)
if not val.get("exists", True):
    continue
person_pk = val.get("person")      # stays .get()
role_pk   = val.get("role")
if person_pk not in valid_person_pks:
    ...
```

```python
val = cast(MediaAttachmentClaimValue, claim.value)
asset_pk = val.get("media_asset")          # stays .get()
category = val.get("category")
is_primary = val.get("is_primary", False)
```

The TypedDict Required/NotRequired split still encodes the true post-10.2 wire shape — that's what mypy sees when it checks `val.get("person")` (returns `int | None` here because `.get()` without default widens the type). Callers doing `if person_pk is None: continue` or `if person_pk not in valid_person_pks` narrow from there, same as today.

**Done when:** each resolver has `cast(<Schema>, claim.value)` at the top of its loop body. Every existing `.get()` call, skip-on-None check, and PK-validity narrow stays byte-identical — the subscript flip for Required keys is Step 10.4's work, not Phase B's.

### Phase C — Type keystone helpers

Annotate in callee-before-caller order:

- [\_helpers.py](../../../backend/apps/catalog/resolve/_helpers.py): `validate_check_constraints(obj: models.Model) -> None`; `_coerce(model_class: type[models.Model], attr: str, value: object) -> object`; `_resolve_fk_generic(..., value: object, ...)`; **`_annotate_priority(qs: QuerySet[Claim]) -> QuerySet[Claim]`** (kills ~9 `no-untyped-call` errors). Only [\_media.py:181](../../../backend/apps/catalog/resolve/_media.py#L181) reads `effective_priority`, and it already uses `cast(HasEffectivePriority, claim)` — keep it.
- [\_entities.py](../../../backend/apps/catalog/resolve/_entities.py): `_sync_markdown_references(obj: models.Model)`; `_resolve_single(obj: models.Model, ...)`; `_resolve_bulk(model_class: type[models.Model], ...)`; `resolve_entity(obj: models.Model) -> models.Model`; `resolve_all_entities(model_class: type[models.Model], *, object_ids: set[int] | None = None)`. Flip `extra_data: dict | None = {} if has_extra_data else None` to `JsonBody | None` — both locals mutate the dict, so the covariant `JsonData = Mapping[str, object]` is wrong; invariant `JsonBody = dict[str, object]` is correct per [core/types.py:19-20](../../../backend/apps/core/types.py#L19).
- [\_relationships.py](../../../backend/apps/catalog/resolve/_relationships.py): `_resolve_aliases(parent_model: type[models.Model], claim_field_name: str)`; `_resolve_parents(parent_model: type[models.Model], *, claim_field_prefix: str | None = None)`. Reverse-relation accessors (`parent_model.aliases.rel`, `parent_model.parents.through`) are category-#3 `Any` per the idiom — Django's descriptor API genuinely discards the info. Confine the ignores to two small helpers:
  - `_get_alias_rel_info(parent: type[models.Model]) -> tuple[type[models.Model], str]` — returns `(alias_model, fk_col)` from `parent.aliases.rel` with a single `# type: ignore[attr-defined]` + comment naming the GenericRelation reverse-accessor constraint.
  - `_get_parents_through(parent: type[models.Model]) -> type[models.Model]` — returns `parent.parents.through`, same pattern.

  A Protocol can't express `parents.through` (or the `.rel.field.name` path), so helper-with-ignore is the minimum-touch option; scattering the ignores across `_resolve_aliases` / `_resolve_parents` loop bodies would be easier to accidentally normalize.

- [\_\_init\_\_.py](../../../backend/apps/catalog/resolve/__init__.py): the `dict | None` / `dict` generics on `sfl_map`, `extra_data`, `_apply_resolution` signatures.

**Done when:** every function in `resolve/` has a full signature; `no-untyped-call` entries on `_annotate_priority` are gone across all five files.

### Phase D — Clean up tuple-reuse in `_relationships.py` and `_media.py`

Two files, same pattern: a loop variable gets assigned from `values_list(...)` with one tuple arity and then reassigned in a later scope (either a different values_list, or a model instance from `in_bulk`). Mypy locks in the first-seen type and flags every divergence.

- `_relationships.py` — baseline lines 81–92 and siblings. ~6 loops across `_resolve_machine_model_m2m`, `resolve_all_gameplay_features`, `resolve_all_credits`, both abbreviation resolvers, `_resolve_aliases`, `_resolve_parents`. `resolve_all_gameplay_features` in particular has the same tuple-vs-instance collision as `_media.py`: [line 253-258](../../../backend/apps/catalog/resolve/_relationships.py#L253) uses `row` for a `values_list` tuple, then [line 294](../../../backend/apps/catalog/resolve/_relationships.py#L294) reassigns `row = rows[pk]` to a `MachineModelGameplayFeature` instance and writes `row.count = count` — this triggers three baseline entries (`[assignment]`, `[method-assign]`, second `[assignment]`) that all collapse when the inner-loop local is renamed (`mgf_row` or similar). Same rename-the-inner-local fix as `_media.py`, not just the inline-unpack fix.
- `_media.py` — baseline entries at [\_media.py:244-250](../../../backend/apps/catalog/resolve/_media.py#L244) (values_list row) colliding with [\_media.py:293](../../../backend/apps/catalog/resolve/_media.py#L293) (`row = rows[update.row_pk]` — the `EntityMedia` instance). Rename the inner-loop local (`media_row` or similar).

Fix by inline-unpacking the tuple at the loop header and renaming any colliding inner-scope reuse:

```python
# before
for row in MachineModelGameplayFeature.objects.filter(...).values_list(
    "pk", "machinemodel_id", "gameplayfeature_id", "count"
):
    pk, mid, fk_id, count = row
    ...

# after
for pk, mid, fk_id, count in MachineModelGameplayFeature.objects.filter(...).values_list(
    "pk", "machinemodel_id", "gameplayfeature_id", "count"
):
    ...
```

Order after Phase C so collateral `no-untyped-call` errors are already gone.

**Done when:** baseline for `resolve/_relationships.py` and `resolve/_media.py` is zero.

## Ordering

A → B → C → D.

- A is independent, small, reviewable.
- B depends on A (needs the TypedDicts to exist).
- C is technically independent of A/B but sequenced here so C's collateral errors don't mask B review.
- D after C (C removes the `no-untyped-call` noise that otherwise clutters D's diff).

## Critical files

- `backend/apps/catalog/resolve/_claim_values.py` — **new**, the vocabulary module.
- `backend/apps/catalog/resolve/_helpers.py` — `_annotate_priority` annotation is the keystone.
- `backend/apps/catalog/resolve/_relationships.py` — 915 lines, bulk of the wiring + tuple cleanup.
- `backend/apps/catalog/resolve/_entities.py`, `_media.py`, `__init__.py` — smaller wiring passes.

## Reuse

- `JsonBody` from [apps/core/types.py](../../../backend/apps/core/types.py) — invariant `dict[str, object]` alias for mutable JSON-shaped dicts. Use for `extra_data` locals and signatures that build up the dict. `JsonData` (covariant `Mapping[str, object]`) is for read-only params; don't use it where the code assigns into the dict.
- `HasEffectivePriority` from [apps/provenance/typing.py](../../../backend/apps/provenance/typing.py) — existing protocol, one read site in `_media.py` keeps its `cast`.
- `ClaimIdentity` / `EntityKey` from [apps/core/types.py](../../../backend/apps/core/types.py) — already used in `_media.py`; carry the pattern.
- NamedTuple shapes in `_media.py` (`CtInfo`, `PrimaryCandidate`, `AttachmentTimestamp`, `MediaRowState`, `EntityCategoryKey`) — the template for any incidental tuple-shape cleanup that falls out of Phase D.

## Non-goals

- Not introducing dataclass factories or Pydantic Schemas for claim values. Rejected: once 10.2 lands, the write path validates every shape; a read-side validator would be a second source of truth with no correctness win. Until 10.2 lands, the existing `.get()`-based defensive reads already do minimal shape checking at the read side.
- Not refactoring `_resolve_single` / `_resolve_bulk` / `_apply_resolution` architecturally.
- Not consolidating the three parallel M2M / abbreviation / alias diff-and-apply patterns — larger refactor, out of mypy scope.

## Verification

- `./scripts/mypy` — expect baseline `new: 0` at every phase, `fixed: >0` at B/C/D.
  - After A: unchanged baseline (no wiring).
  - After C: the ~9 `no-untyped-call` entries on `_annotate_priority` gone; `no-untyped-def` entries on `_helpers.py` / `_entities.py` gone.
  - After D: `_relationships.py` and `_media.py` baselines at zero.
- `uv run --directory backend pytest apps/catalog/tests/test_resolve*.py apps/catalog/tests/test_bulk_resolve*.py` — behavior-preserving; all resolver tests pass.
- `make ingest` end-to-end — exercises real bulk-resolution paths against R2 data. Not gating, but the natural integration test.
- After each phase, sync baseline with `uv run --directory backend mypy --config-file pyproject.toml . 2>&1 | uv run --directory backend mypy-baseline sync` once `./scripts/mypy` reports `new: 0`.

## Design decisions locked in after review

- **TypedDicts (not dataclass factories or Pydantic Schemas).** Read-side shape documentation only; zero runtime cost. Factories would duplicate write-path validation (post-10.2).
- **`cast` is documentation-only in 10.3.** `.get()` stays everywhere, required and optional alike. Subscript flip for required keys happens in Step 10.4 after [ProvenanceValidationTightening.md](ProvenanceValidationTightening.md) lands.
- **`exists` is Required on all 7 TypedDicts.**
- **No `M2MClaimValue` TypedDict.** Generic M2M resolver uses `Mapping[str, object]` + `isinstance`.
- **Introspection confined to helpers.** `_get_alias_rel_info` and `_get_parents_through` isolate the `# type: ignore[attr-defined]` to one line each.
- **TypedDicts live in `resolve/_claim_values.py` for now.** Move to `apps.catalog.claims.types` later if claim builders get typed.
