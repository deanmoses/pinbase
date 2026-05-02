# Series Credits Through Claims

A standing violation of the "all catalog fields are claims-based" rule: Series credits bypass provenance. This doc closes that hole on its own grounds, independent of any larger metadata refactor.

## Problem

`Credit` is XOR-shaped: a row attaches either a `MachineModel` or a `Series`, never both. The MachineModel side goes through claims end-to-end. The Series side bypasses claims entirely:

- **Ingest writes `Credit(series=...)` rows directly** at [ingest_pindata.py:1397](../../backend/apps/catalog/management/commands/ingest_pindata.py#L1397). No `Claim`, no `ChangeSet`, no provenance.
- **The resolver only handles MachineModel.** [\_relationships.py:327](../../backend/apps/catalog/resolve/_relationships.py#L327) hardcodes `ContentType.objects.get_for_model(MachineModel)` and only reads/writes `Credit.model_id`. A hypothetical `content_type=Series, field_name="credit"` claim would be silently ignored; an existing `Credit` row with `series_id` set is never touched by the resolver.
- **No edit-claims path exists** for series credits today ([edit_claims.py](../../backend/apps/catalog/api/edit_claims.py) has no Series/credit handling).

So Series credits are structural inserts whose only writer is one ingest command. That violates [CLAUDE.md](../../CLAUDE.md)'s non-negotiable: every field on catalog models must go through claims, including relationships, with no "only one source today" exemption.

## Target shape

Symmetric to MachineModel credits. Claim keying at ingest follows the existing pattern in [ingest_pindata.py:1848-1866](../../backend/apps/catalog/management/commands/ingest_pindata.py#L1848-L1866):

```python
# Series credit claim — same payload shape as MachineModel credit claim
Claim(
    content_type_id=series_ct_id,  # ← was MachineModel CT for model credits
    object_id=series_obj.pk,
    field_name="credit",
    claim_key=claim_key,  # from build_relationship_claim("credit", {...})
    value={"person": person_pk, "role": role_pk},
)
```

Resolution materializes these into `Credit(series=series_obj, person=..., role=...)` rows — the XOR branch is determined by the claim's `content_type`.

## Work items

1. **Rewrite the Series-credit ingest path.** [ingest_pindata.py:1380-1407](../../backend/apps/catalog/management/commands/ingest_pindata.py#L1380-L1407): replace the direct `Credit(series=...)` bulk_create with claim assertion, mirroring the MachineModel credit block at [ingest_pindata.py:1848-1866](../../backend/apps/catalog/management/commands/ingest_pindata.py#L1848-L1866). Uses the same `build_relationship_claim("credit", ...)` helper.

2. **Restructure `resolve_all_credits` to key on `(content_type, object_id)` throughout.** This is not a filter swap — every internal structure in the current resolver ([\_relationships.py:320-400](../../backend/apps/catalog/resolve/_relationships.py#L320-L400)) is keyed by `model_id: int` (`winners_by_model`, `desired_by_model`, `existing_by_model`, the final `for model_id in all_model_ids` loop, the `Credit(model_id=..., ...)` construction). Change: key every dict by a `(content_type_id, object_id)` tuple, read claims for both `MachineModel` and `Series` CTs, and branch at the `Credit(...)` constructor to pick `model=` vs `series=`. Existing-row queries become a union — one pass over `Credit.objects.filter(model_id__in=...)` and one over `series_id__in=...`. Constraint coverage is already symmetric: `Credit` has matching partial-unique constraints for each branch plus a CHECK that enforces exactly one FK is set, so no schema work is needed. Stays bespoke: XOR branch-selection logic doesn't fit the generic resolver contract and the generic resolver isn't on the near-term roadmap anyway.

3. **Keep `subject_ids` as `set[int]`, scoped to one branch per call.** After the `subject_ids` standardization sweep ([commit 2eea1ebaf](https://github.com/deanmoses/pindata/commit/2eea1ebaf)), bespoke resolvers take `subject_ids: set[int] | None = None`. The natural extension for XOR is two calls — one with MachineModel pks, one with Series pks — each scoped to its branch. Callers (signal handlers, ingest tail, tests) are already scoped to one model class apiece, so there's no "single-call contract" to preserve. A dict-by-CT shape (`subject_ids_by_ct`) would break the uniform signature across bespoke resolvers for exactly one caller and add real complexity for a speculative future benefit. Implementation: when `subject_ids` is passed, the resolver needs to know which branch it applies to — either infer from a second kwarg (`subject_ct: ContentType`) or split into two entry points (`resolve_all_model_credits` / `resolve_all_series_credits`) that share a helper. Two entry points is probably cleaner.

4. **Confirm cache invalidation covers Series credits.** The cache-invalidation model-set walk ([commit 38227de76](https://github.com/deanmoses/pindata/commit/38227de76)) derives which models invalidate which pages via the app registry. Today `Credit` writes only land via the MachineModel branch, so Series page invalidation on Credit changes may or may not already be wired. Verify that writing `Credit(series=...)` via the resolver invalidates the Series page cache; if not, wire it. This is small but easy to miss — Series pages will silently serve stale data otherwise.

5. **Tests.** Mirror existing MachineModel credit tests ([test_resolve_credits.py](../../backend/apps/catalog/tests/test_resolve_credits.py), [test_bulk_assert_claims.py](../../backend/apps/catalog/tests/test_bulk_assert_claims.py)) for the Series branch: claim → resolver → row; conflicting sources; deletion when a winner disappears. Also cover the XOR invariant: a Series credit claim must not produce a row with `model_id` set, and vice versa (the CHECK constraint will catch it at the DB, but a resolver test pins the intent).

6. **Existing Series credit rows.** Any `Credit` row with `series_id` set in the current DB was written without a claim. Once item 1 lands, re-running `make ingest` produces the claims naturally — ingest is idempotent and claim assertion is the ingest path. Options are: (a) re-run ingest, which will leave pre-existing rows orphaned from any claim until the resolver deletes them on the next resolve pass (since no claim will have asserted them, the claim-driven resolver will treat them as losers and delete); (b) DB reset, since we're pre-launch. Both converge to the same state. (b) is faster and avoids a transient window where rows exist without claims; prefer it unless there's a reason to preserve current rows.

## Non-goals

- **User-facing Series credit editing.** No edit-claims API endpoint is proposed here. If/when series pages get credit editing, the claim machinery will already be in place.
- **Generic/bespoke resolver split.** `resolve_all_credits` stays bespoke. Folding it into a spec-driven generic resolver would only become relevant if [ModelDrivenCatalogRelationshipMetadata.md](model_driven_metadata/ModelDrivenCatalogRelationshipMetadata.md) is un-deferred, and even then Credit would stay bespoke because of the XOR write logic.

## Relation to model-driven metadata

[ModelDrivenCatalogRelationshipMetadata.md](model_driven_metadata/ModelDrivenCatalogRelationshipMetadata.md) is currently deferred; this doc is not gated on it and stands alone as a provenance-compliance fix. If that spec work is un-deferred later, having Credit flow through claims end-to-end is a clean precondition — the spec describes `Credit` as an `XorSubject` shape, which is only honest if both FK branches actually flow through claims. Land this doc's work whenever; the spec-related framing around `XorSubject` is a "for when/if we get there" note, not a dependency in either direction.
