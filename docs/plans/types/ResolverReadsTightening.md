# Resolver Reads Tightening

## Status: OPEN

Not landed. Resolver code still uses `.get()` for required relationship payload keys; this remains Step 5 of [ResolveHardening.md](ResolveHardening.md).

Follow-up to [ProvenanceValidationTightening.md](ProvenanceValidationTightening.md): once the write-path validator guarantees relationship-claim payloads have all their required keys at the right scalar types, the read side in `catalog/resolve/*.py` can drop defensive `.get()` calls in favor of subscript access. Behavior-preserving; the runtime contract didn't change, only mypy's knowledge of it did.

This is Step 5 of [ResolveHardening.md](ResolveHardening.md) (originally Step 10.4 of [MypyFixing.md](MypyFixing.md)). Its own PR with its own gates — see Prerequisites.

## Prerequisites

- **[ProvenanceValidationTightening.md](ProvenanceValidationTightening.md) landed.** Both Commit A (registry scaffolding) and Commit B (classifier + validator + cleanup). The write path must now reject payloads missing any required registered key, so a `val["person"]` read can't KeyError on a freshly written malformed row.
- **Post-Step-2 wipe + re-ingest done.** The validator only constrains rows _written after_ it lands. Any pre-validator row missing a required key would KeyError on subscript access here. Step 2's commit sequence includes a post-merge wipe + re-ingest ([ProvenanceValidationTightening.md § Data posture](ProvenanceValidationTightening.md)); this step must not land until that has happened.
- **[CatalogResolveTyping.md](CatalogResolveTyping.md) Phase B landed.** Every resolver loop already has `cast(<Schema>, claim.value)` at the top. This step only flips the reads, not the types.

If a key is subscript-accessed here but the corresponding namespace isn't registered in the write-path validator, the flip is unsafe. Double-check coverage against the registration list in [ProvenanceValidationTightening.md § "New register_relationship_schema call sites"](ProvenanceValidationTightening.md) before flipping.

## Rule

**Subscript access for `Required` keys on the TypedDict; `.get()` stays for `NotRequired` keys.** The TypedDict definitions in `backend/apps/catalog/resolve/_claim_values.py` are the authoritative source for which is which.

## Specific flips

In [\_relationships.py](../../../backend/apps/catalog/resolve/_relationships.py) and [\_media.py](../../../backend/apps/catalog/resolve/_media.py):

- `val.get("exists", True)` → `val["exists"]`. Negate: `if not val["exists"]:`. All 7 relationship TypedDicts have `exists` Required.
- `val.get("person")` → `val["person"]` (credits).
- `val.get("role")` → `val["role"]` (credits).
- `val.get("alias_value", "")` → `val["alias_value"]` (all 7 alias resolvers). The `""` default goes away — required now.
- `val["value"]` — already subscript in `resolve_all_{title,model}_abbreviations`; keep as-is.
- `val.get("parent")` → `val["parent"]` (theme + gameplay-feature parents).
- `val.get("location")` → `val["location"]` (CorporateEntity → Location).
- `val.get("gameplay_feature")` → `val["gameplay_feature"]` (gameplay-feature M2M).
- `val.get("media_asset")` → `val["media_asset"]` (media attachments).

## Stays as `.get()`

`NotRequired` keys — these are genuinely optional on the wire and the write path doesn't require them:

- `val.get("count")` — gameplay_feature count.
- `val.get("alias_display")` — aliases.
- `val.get("category")` — media attachments.
- `val.get("is_primary", False)` — media attachments.

## Generic M2M resolver — stays `Mapping[str, object]`

`_resolve_machine_model_m2m` at [\_relationships.py:86](../../../backend/apps/catalog/resolve/_relationships.py#L86) reads `val.get(spec.field_name)` with a runtime key. It's not covered by a TypedDict because the key varies per spec. ProvenanceValidationTightening guarantees the value is present and is a true `int` (not `bool`), so a subscript-with-type-narrow reads as a defensive post-validation guard:

```python
target_pk = val[spec.field_name]
if type(target_pk) is not int:  # matches write-path validator's rule; excludes bool
    continue
```

`type(target_pk) is not int` intentionally mirrors the write-path rejection rule from ProvenanceValidationTightening: `bool` is a subclass of `int` in Python, and the validator rejects `{"theme": True}` as a PK — the read side does the same. Don't loosen to `isinstance`.

Judgment call whether to make that swap as part of this step or leave it. Default: leave it. The typing here is `Mapping`-based, not TypedDict-based, so the rationale for the flip is weaker and the readability win is small. Flip only if it simplifies surrounding code.

## Verification

- `./scripts/mypy` — baseline unchanged (subscript access on a TypedDict's Required key type-checks the same as `.get()` did).
- `uv run --directory backend pytest apps/catalog/tests/test_resolve*.py apps/catalog/tests/test_bulk_resolve*.py` — all pass.
- `make ingest` end-to-end — exercises real bulk-resolution paths. Any KeyError here means a namespace slipped through ProvenanceValidationTightening's coverage; the fix is to add the registration there, not to revert this PR.

## Non-goals

- No new tests. Behavior-preserving; existing resolver tests cover.
- No TypedDict changes. The Required/NotRequired split was set in [CatalogResolveTyping.md](CatalogResolveTyping.md) Phase A and reflects the post-ProvenanceValidationTightening wire contract.
- No changes to optional `.get()` reads. They stay defensive because the wire shape is genuinely optional.
