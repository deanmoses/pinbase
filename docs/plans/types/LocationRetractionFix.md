# Location Retraction Fix

Step 10.1 of [MypyFixing.md](MypyFixing.md). Small TDD-first behavior fix: `resolve_all_corporate_entity_locations` currently ignores `exists=False` on `location` claims, so retractions don't retract. Independent of the rest of Step 10 — can land any time.

## Bug

[resolve_all_corporate_entity_locations](../../../backend/apps/catalog/resolve/_relationships.py#L852) at [\_relationships.py:876-882](../../../backend/apps/catalog/resolve/_relationships.py#L876) reads claims via `.values("object_id", "value")` and extracts `loc_pk` without ever checking `val.get("exists", True)`:

```python
active_claims = claims_qs.values("object_id", "value")

desired: dict[int, set[int]] = defaultdict(set)
for row in active_claims:
    loc_pk = (row["value"] or {}).get("location")
    if loc_pk and loc_pk in valid_loc_pks:
        desired[row["object_id"]].add(loc_pk)
```

Effect: a claim written as `{"location": 42, "exists": False}` — the canonical retraction shape, meaning "this CE is NOT at Location 42 anymore" — still adds `42` to `desired`, so the resolver creates or preserves the `CorporateEntityLocation` row. Retractions silently no-op.

Every other relationship resolver in the same file checks `if not val.get("exists", True): continue` before consuming the payload. This one was missed.

## Fix

Honor `exists=False` the same way every sibling resolver does. One guard added to the claim-reading loop.

## TDD plan

1. **Failing test** — in [apps/catalog/tests/test_bulk_resolve_corporate_entity_locations.py](../../../backend/apps/catalog/tests/) (or wherever the existing CE-location resolver tests live):
   - Seed a `CorporateEntity` and a `Location`.
   - Write an active `location` claim with value `{"location": <loc_pk>, "exists": False}` for the CE.
   - Run `resolve_all_corporate_entity_locations()`.
   - Assert the `CorporateEntityLocation` row is absent.
   - Second assertion: if the row existed pre-resolution, it should be removed.
2. Run the test; confirm it fails for the right reason (row present / not removed).
3. Add the `exists` guard to the loop body:
   ```python
   for row in active_claims:
       val = row["value"] or {}
       if not val.get("exists", True):
           continue
       loc_pk = val.get("location")
       if loc_pk and loc_pk in valid_loc_pks:
           desired[row["object_id"]].add(loc_pk)
   ```
4. Re-run; test passes.

No changes to the wider resolver logic. `.get("location")` stays `.get()` — the subscript flip for this namespace happens in [ResolverReadsTightening.md](ResolverReadsTightening.md) after [ProvenanceValidationTightening.md](ProvenanceValidationTightening.md) registers the `location` namespace schema.

## Verification

- The new test passes.
- `uv run --directory backend pytest apps/catalog/tests/test_bulk_resolve*.py apps/catalog/tests/test_resolve*.py` — all green.
- `./scripts/mypy` — baseline unchanged (no typing impact).

## Non-goals

- Not tightening the write path. Someone writing `exists=False` on a location claim today succeeds; the resolver-side bug is independent. Write-path tightening is [ProvenanceValidationTightening.md](ProvenanceValidationTightening.md).
- Not changing any typing. The typing pass is [CatalogResolveTyping.md](CatalogResolveTyping.md) (Step 10.3).
