# Provenance Validation Tightening

## Context

The provenance write path admits malformed relationship claims through three independent holes. Each one is a silent-data-loss path today:

- **`assert_claim` bypasses relationship validation.** [claim.py:121-127](../../../backend/apps/provenance/models/claim.py#L121) classifies each claim and only validates `DIRECT` payloads; `RELATIONSHIP` passes through untouched. User edits via `execute_claims` → `assert_claim` therefore never reach any relationship shape check.
- **Malformed payloads misclassify as EXTRA.** [classify_claim](../../../backend/apps/provenance/validation.py#L86) returns `RELATIONSHIP` only if `"exists" in value`. On any model with an `extra_data` field (MachineModel, Title, …), a malformed credit/theme/alias payload lacking `"exists"` falls through to `EXTRA` and gets silently stored as free-form staging data — never hitting the relationship validator at all.
- **Literal namespaces have no schema.** [validate_relationship_claims_batch](../../../backend/apps/provenance/validation.py#L359) only validates namespaces registered via `register_relationship_targets`, which covers FK value_keys. Aliases (`alias_value`, `alias_display`) and abbreviations (`value`) are intentionally unregistered today and pass through without any schema check.

We're pre-launch. Loosening later is a one-line change; tightening later requires auditing every production row. **Err tight.**

This work also unblocks [Step 10.4 of MypyFixing.md](MypyFixing.md#step-104-subscript-flip-in-catalogresolve) — the resolver read path can flip from `cast + .get()` to subscript access for required keys once the write path guarantees them.

## Non-goals

- **Not adding target-existence validation to the single-write path.** Existence stays batch-only. `validate_relationship_claims_batch` already groups claims by namespace and issues one SQL query per group — cheap amortized. Doing the same check in `assert_claim` would be one query per claim, and `execute_claims` writes many claims per user edit (e.g. editing a Title's gameplay features). The brief window of tolerated stale FK targets is an explicit trade-off: stale targets get caught at the next bulk resolve. If we later see drift in practice, benchmark before changing.
- **Not reworking `extra_data` semantics.** Claims that genuinely belong in `EXTRA` (unrecognized field names on models with `extra_data`) still flow through untouched.
- **Not touching DIRECT claim validation.** `validate_claim_value` stays as-is.

## Design

### Registry API

New module-level registry of relationship schemas. Sits alongside the existing `_relationship_target_registry` (which this work subsumes) in [apps/provenance/validation.py](../../../backend/apps/provenance/validation.py).

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ValueKeySpec:
    """One key in a relationship claim's value dict."""
    name: str
    scalar_type: type  # int, str, or bool — matched with `type(v) is scalar_type`
    required: bool
    nullable: bool = False  # True allows `None` in addition to scalar_type
    fk_target: tuple[type[models.Model], str] | None = None
    # If set, (target_model, lookup_field) — this value_key is an FK reference
    # and batch-path existence checks apply via validate_relationship_claims_batch.

@dataclass(frozen=True, slots=True)
class RelationshipSchema:
    namespace: str  # claim field_name, e.g. "credit", "theme_alias", "abbreviation"
    value_keys: tuple[ValueKeySpec, ...]

_relationship_schemas: dict[str, RelationshipSchema] = {}

def register_relationship_schema(schema: RelationshipSchema) -> None:
    _relationship_schemas[schema.namespace] = schema
```

The existing `register_relationship_targets` becomes a thin shim: its input is `dict[str, list[tuple[str, type[Model], str]]]` (each namespace maps to a list of `(value_key, target_model, lookup_field)` tuples — e.g. `credit` has two entries, `person` and `role`). The shim builds **one `ValueKeySpec` per tuple in the list**, all marked required with `scalar_type=int` and `fk_target=(target_model, lookup_field)`, then delegates to `register_relationship_schema`. Preserves existing call sites; no sweeping refactor.

Namespaces registered (full coverage — must match the read-side TypedDicts in `catalog/resolve/_claim_values.py`):

- `"credit"` → `{person: int (required, fk=Person.pk), role: int (required, fk=CreditRole.pk)}`
- `"gameplay_feature"` → `{gameplay_feature: int (required, fk=GameplayFeature.pk), count: int | None (optional)}`
- `"theme"` / `"tag"` / `"reward_type"` → `{<namespace>: int (required, fk=<target>.pk)}`
- `"theme_alias"` / `"manufacturer_alias"` / `"person_alias"` / `"gameplay_feature_alias"` / `"reward_type_alias"` / `"corporate_entity_alias"` / `"location_alias"` → `{alias_value: str (required), alias_display: str (optional)}`
- `"abbreviation"` → `{value: str (required)}` — shared by Title and MachineModel resolvers (same `field_name`, distinguished by `content_type`); registry keyed by `field_name` alone is fine today because both share the shape.
- `"media_attachment"` → `{media_asset: int (required, fk=MediaAsset.pk), category: str | None (optional), is_primary: bool (optional)}`
- `"location"` (CorporateEntity → Location) → `{location: int (required, fk=Location.pk)}`
- `"theme_parent"` / `"gameplay_feature_parent"` → `{parent: int (required, fk=<self>.pk)}`

### Classification change

Preserve DIRECT precedence. Keep the existing `field_name in claim_fields → DIRECT` check first. **After** DIRECT detection, classify any remaining `field_name` appearing in `_relationship_schemas` as `RELATIONSHIP` regardless of whether `"exists"` is present. The new registry check **replaces** the old structural relationship check (`claim_key != field_name and isinstance(value, dict) and "exists" in value`) for non-direct fields; it does **not** override legitimate direct fields whose name collides with a relationship namespace.

### Single-claim validator

Factor a new `validate_single_relationship_claim(claim: Claim) -> None` out of `validate_relationship_claims_batch`. Raises `ValidationError` on shape violation. Called from:

- `ClaimManager.assert_claim` at [claim.py:127](../../../backend/apps/provenance/models/claim.py#L127), in a new branch for `ct_result == RELATIONSHIP` that propagates the `ValidationError`.
- `validate_claims_batch` at [validation.py:251](../../../backend/apps/provenance/validation.py#L251), replacing the accumulate-then-batch-validate path for shape. Existence checks remain batched in `validate_relationship_claims_batch`.

### Rejection conditions (shape)

Applied by `validate_single_relationship_claim` in both paths:

- `value` is not a `dict`.
- `value` is missing `"exists"`, or `value["exists"]` is not a `bool`.
- Missing any **required** registered `ValueKeySpec` for the namespace. Optional keys are type-checked only when present.
- Wrong scalar type for any present registered key (required or optional). Applies to identity keys (`person: int`, `alias_value: str`) and non-identity keys (`count: int | None`, `category: str | None`, `is_primary: bool`, `alias_display: str`).

**Why `type(value) is scalar_type`, not `isinstance(value, scalar_type)`.** `bool` is a subclass of `int` in Python, so `isinstance(True, int)` is `True`. A payload carrying `{"person": True}` or `{"count": False}` should be rejected, not silently accepted as PK `1` / count `0`. The primary threat is Python-side code (tests, ingest adapters) passing bools where ints belong; `json.loads` of `{"x": true}` also produces `bool`, so the rule catches wire payloads too. Future readers should not loosen this to `isinstance`. For `nullable=True` specs, accept `None` in addition to `type(v) is scalar_type`.

### Rejection conditions (existence — batch only)

Unchanged from today. `validate_relationship_claims_batch` continues to do per-namespace group queries for FK `ValueKeySpec`s where `exists=True`. `assert_claim` does not do existence checks — see Non-goals.

## Commit sequence

The audit can't run before the registry exists. Split into two commits:

1. **Commit A — registry scaffolding (no behavior change).** Add `ValueKeySpec` / `RelationshipSchema` / `register_relationship_schema` to [validation.py](../../../backend/apps/provenance/validation.py). Reshape `register_relationship_targets` into a shim that constructs an FK-only `RelationshipSchema` and delegates. Add new `register_relationship_schema` call sites for every currently-unregistered namespace (list below). At this point `classify_claim` still uses the old structural check and the batch validator still uses `value.get(value_key)` — runtime behavior is identical. Mypy passes, tests pass, baseline unchanged.

2. **Audit against prod snapshot.** Run `scripts/audit_relationship_claims.py` (below) using Commit A's registry against a prod DB. Record counts + breakdown. Expected outcome on a clean pre-launch DB: all zeros. Non-zero counts inform Commit B.

3. **Commit B — classifier, validator, cleanup.** Flip `classify_claim` to registry-driven classification (preserving DIRECT precedence). Add `validate_single_relationship_claim`. Wire it into `assert_claim` and `validate_claims_batch`. If the audit found offending rows, include the `Claim.objects.filter(...).update(is_active=False)` cleanup in the same commit, with counts and namespace breakdown in the commit message.

This sequencing makes the "audit first" rule literal instead of aspirational, and keeps the behavior-changing commit small enough to review.

### New `register_relationship_schema` call sites

All registrations live in [apps/catalog/claims.py](../../../backend/apps/catalog/claims.py) alongside the existing `register_relationship_targets` calls. For full coverage, Commit A must add **every** namespace below. Missing one means resolver reads for that namespace stay unvalidated and Step 10.4 of MypyFixing.md can't subscript those keys safely.

- **Alias namespaces (7):** `theme_alias`, `manufacturer_alias`, `person_alias`, `gameplay_feature_alias`, `reward_type_alias`, `corporate_entity_alias`, `location_alias`. Each → `{alias_value: str (required), alias_display: str (optional)}`. Net-new.
- **Abbreviation namespace (1):** `abbreviation` → `{value: str (required)}`. Shared by Title and MachineModel resolvers — one registration covers both. Net-new.
- **Parent namespaces (2):** `theme_parent`, `gameplay_feature_parent`. Each → `{parent: int (required, fk=<self>.pk)}`. Net-new.
- **Location namespace (1):** `location` (CorporateEntity → Location) → `{location: int (required, fk=Location.pk)}`. Net-new.
- **Credit namespace (1):** `credit` → `{person: int (required, fk=Person.pk), role: int (required, fk=CreditRole.pk)}`. **Migration** — already registered as FK-only today; new API call replaces it.
- **Gameplay feature namespace (1):** `gameplay_feature` → `{gameplay_feature: int (required, fk=GameplayFeature.pk), count: int | None (optional)}`. **Migration + add `count` spec.**
- **Simple M2M namespaces (3):** `theme`, `tag`, `reward_type`. Each → `{<namespace>: int (required, fk=<target>.pk)}`. **Migration.**
- **Media attachment namespace (1):** `media_attachment` → `{media_asset: int (required, fk=MediaAsset.pk), category: str | None (optional), is_primary: bool (optional)}`. **Migration + add `category` / `is_primary` specs.**

17 namespaces total — 11 net-new, 6 migrations from the old FK-only API.

## Audit queries

Draft the script below into `scripts/audit_relationship_claims.py` (or a Django management command) and run against a production DB snapshot after Commit A lands but before Commit B. Counts and breakdowns go in the Commit B PR description.

```python
# scripts/audit_relationship_claims.py
"""One-shot audit ahead of ProvenanceValidationTightening.

Reports three counts:
  a. Active claims where field_name is a relationship-registry name but
     classify_claim currently returns EXTRA (the silent-fallthrough case).
  b. Active claims under a registered relationship namespace whose value
     fails the new shape rejection conditions (non-dict, missing/non-bool
     exists, missing required key, wrong scalar type).
  c. A breakdown of (b) by namespace so we know what to deactivate.
"""
from collections import Counter

from apps.provenance.models import Claim
from apps.provenance.validation import (
    EXTRA,
    _relationship_schemas,   # Commit A adds this registry; script runs after Commit A.
    classify_claim,
)
from apps.core.models import get_claim_fields


def reason_for_rejection(value: object, schema: "RelationshipSchema") -> str | None:
    if not isinstance(value, dict):
        return "not-dict"
    exists = value.get("exists")
    if not isinstance(exists, bool):
        return "missing-or-non-bool-exists"
    for spec in schema.value_keys:
        v = value.get(spec.name)
        if v is None:
            if spec.required and not spec.nullable:
                return f"missing-required-{spec.name}"
            continue
        if spec.nullable and v is None:
            continue
        if type(v) is not spec.scalar_type:
            return f"wrong-type-{spec.name}"
    return None


def run() -> None:
    namespaces = set(_relationship_schemas.keys())

    # (a) silent EXTRA fallthrough
    a_count = 0
    for claim in Claim.objects.filter(is_active=True, field_name__in=namespaces).iterator():
        model_class = claim.content_type.model_class()
        if model_class is None:
            continue
        ct = classify_claim(
            model_class, claim.field_name, claim.claim_key, claim.value,
            claim_fields=get_claim_fields(model_class),
        )
        if ct == EXTRA:
            a_count += 1

    # (b) + (c) shape violations by namespace
    breakdown: Counter[tuple[str, str]] = Counter()
    b_count = 0
    for schema in _relationship_schemas.values():
        for claim in Claim.objects.filter(
            is_active=True, field_name=schema.namespace
        ).iterator():
            reason = reason_for_rejection(claim.value, schema)
            if reason:
                breakdown[(schema.namespace, reason)] += 1
                b_count += 1

    print(f"(a) silent-EXTRA-fallthrough active claims: {a_count}")
    print(f"(b) shape-violation active claims: {b_count}")
    print("(c) breakdown by (namespace, reason):")
    for (ns, reason), n in sorted(breakdown.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>6}  {ns}  {reason}")
```

Run on a prod DB snapshot (`railway ssh` + DJANGO_SETTINGS connection, or a fresh `make pull-ingest` against current data). Expected outcome on a clean pre-launch DB: all zeros. Any non-zero count is either a legacy ingest artifact (deactivate in the cleanup step) or a bug in the script — investigate before writing the validator.

## TDD plan

Assumes the "Commit sequence" above: Commit A (registry scaffolding) → audit → Commit B (classifier + validator + cleanup). Tests land with Commit B.

1. **Commit A is not TDD-gated.** It's pure scaffolding — new types, new no-op register calls. Mypy and existing tests must pass; no new tests required.
2. **Run the audit script** (above) against a prod snapshot. Counts + breakdown inform Commit B's PR description.
3. **If audit is all zero:** Commit B is a straight code change — the three tightenings in one PR.
4. **If non-zero:** cleanup step in the same PR — `Claim.objects.filter(...).update(is_active=False)` on offending rows using the breakdown from step 2, with counts and namespace breakdown in the commit message. Don't hand-edit payloads; the audit trail is the truth.
5. **Failing tests, one per rejection mode, per path:**
   - `assert_claim` path: assert `ValidationError` raised for each of — non-dict value, missing `exists`, non-bool `exists`, missing required key, wrong-scalar-type required key, wrong-scalar-type optional key, `bool` passed where `int` expected.
   - Batch path: `validate_claims_batch(...)` returns `(valid, rejected_count)` — assert `rejected_count == 1` and the malformed claim is **not** in `valid`. For rejection-reason assertions, call `validate_relationship_claims_batch(...)` directly (that function returns the rejected `list[Claim]`).
   - Classify-by-registry fix: a malformed relationship payload on a model with `extra_data` must reach the relationship validator (and be rejected), not land as `EXTRA`.
   - DIRECT precedence preserved: a `field_name` that is both a DIRECT claim field on the model **and** a name in the relationship registry must classify as `DIRECT`. (Likely synthetic — no real collision today, but pin the ordering.)
6. Implement the three tightenings. Tests go green.

## Files touched

- [apps/provenance/validation.py](../../../backend/apps/provenance/validation.py) — new `ValueKeySpec` / `RelationshipSchema` / `register_relationship_schema`, classify_claim change, new `validate_single_relationship_claim`, existing `register_relationship_targets` shimmed on top.
- [apps/provenance/models/claim.py](../../../backend/apps/provenance/models/claim.py) — `assert_claim` new `RELATIONSHIP` branch calling `validate_single_relationship_claim`.
- [apps/catalog/claims.py](../../../backend/apps/catalog/claims.py) — migrate existing `register_relationship_targets` call sites to `register_relationship_schema` where they need to register optional non-FK keys (aliases, abbreviations, media-attachment non-identity keys).
- [apps/provenance/tests/test_validation.py](../../../backend/apps/provenance/tests/test_validation.py) — new rejection-mode tests.
- `scripts/audit_relationship_claims.py` — new, one-shot script.

## Verification

- `uv run --directory backend pytest apps/provenance/tests/test_validation.py apps/catalog/tests/test_bulk_resolve*.py` — all tests pass.
- `./scripts/mypy` — baseline unchanged (this step has no mypy impact).
- `make ingest` end-to-end against R2 data — no new rejections on clean data. If rejections appear, they're real malformed payloads upstream ingest is producing and must be fixed at the source.
- After landing, Step 10.4 of MypyFixing.md (resolver subscript flip) is unblocked.
