# Claim-Value Shape Hardening

## Status: PARTIALLY DONE

Steps 1-4 have landed. Step 5 remains open: [ResolverReadsTightening.md](ResolverReadsTightening.md) has not landed yet, and resolver code still uses `.get()` for required relationship payload keys.

## Context

Sequence that tightens the claim-value _shape_ layer — the surfaces that decide what a relationship claim's payload can carry and how resolvers read it back:

1. **Write path** — what can be stored (enforced at runtime).
2. **Registry** — single source of truth for namespace shape.
3. **Read-path types** — TypedDicts that mirror the registry (enforced by a consistency test).
4. **Baseline cleanup** — mypy burn-down on resolver helpers and tuple reuse, bundled here because it touches the same files.
5. **Cleanup** — subscript flip on required keys, plus anything else surfaced while landing Steps 2–4.

The motivation is reasoning clarity. Today, a claim value is opaque JSON and four surfaces can disagree arbitrarily about what it should contain — writers, three separate registries, resolver reads, and each resolver's defensive fallback code. After this sequence there's one runtime write-path authority (the registry + validator) and a tested read-side mirror (the Step 3 consistency test ties TypedDicts to the registry). Mypy then checks the cast-bound resolver reads. What is _not_ mechanically verified: that a resolver casts to the _right_ TypedDict for the namespace it's resolving — a wrong cast would pass mypy and the consistency test. Closing that gap is possible (e.g. a namespace→TypedDict dispatch) but out of scope.

Scope is deliberately narrow to the value-shape layer. Winner selection, priority tiebreaking, dispatch, and `extra_data` semantics are untouched — see Out of scope.

Mypy baseline reduction (~44 entries in `catalog/resolve/*` plus the downstream subscript-flip entries) is a **scoreboard**, not the motivation. Step 4 is where that scoreboard work explicitly lives, bundled with the sequence because it touches the same files as Steps 2–3, not because it's load-bearing for the hardening story. This sequence was originally conceived as Step 10 of [MypyFixing.md](MypyFixing.md); it lives here as its own plan because the reasoning wins justify it independently of the baseline.

## Reasoning wins

The sequence specifically improves the claim-_value-shape_ layer of resolution:

- **"What can this claim carry?" gets one answer.** Today: three registries (`_entity_ref_targets`, `_literal_schemas`, `_relationship_target_registry`) plus per-resolver defensive checking. After Step 2: one `_relationship_schemas` registry. After Step 3: read-path TypedDicts mirror the registry, test-enforced.
- **Required vs. optional becomes explicit at the type level.** `value.get("count", 0)` today tells a reader nothing about whether `count` is guaranteed. After Step 3 the TypedDicts record the distinction; Step 5 flips required-key reads to subscript so intent is visible at the read site too.
- **Silent-drift classes are closed.** Unknown value keys can't accumulate in stored claims. Wrong-subject claims can't silently route to `extra_data`. Malformed retractions that previously bypassed shape validation now go through the same check as positive claims. A future extractor adding a new field forces a schema update rather than making resolvers silently blind to the new data.
- **The write-path contract is mechanically enforced; the read side has a tested mirror.** Writer ↔ registry is tied by write-time validation; registry ↔ TypedDict is tied by the Step 3 consistency test; resolver reads follow via mypy once the casts land. The one link _not_ mechanically verified is cast-site correctness (which TypedDict a resolver casts to for its namespace) — called out in the Context, not closed by this sequence.

## Out of scope

Named so the sequence isn't sold as something it isn't:

- **Resolver business logic is untouched.** Winner selection, priority tiebreaking, and active-vs-all target filtering (e.g. `resolve_all_corporate_entity_locations` filtering `is_active=True` before winner selection) are not in scope. "Why did this source win?" is as hard to reason about as it was.
- **Resolver dispatch stays bespoke.** `_parent_dispatch`, `_custom_dispatch`, `M2M_FIELDS` are explicitly deferred from unification (see [ProvenanceValidationTightening.md](ProvenanceValidationTightening.md) non-goals). "Which resolver runs for this claim?" is still answered by reading scattered code.
- **`extra_data` remains a parallel universe.** Claims with unknown _field_names_ still fall into EXTRA (correctly — that's the staging path). Only unknown _value keys within a registered namespace_ get rejected. **Policy implication for extractor authors:** relationship value payloads are closed schemas. Useful-but-unmodeled relationship data has three paths — register a new namespace, drop the data at the extractor, or store it on the subject's `extra_data`. Adding it to an existing relationship payload will fail validation and block ingest.
- **No meta-invariant against the next Step 1.** The location retraction bug was a point fix. The sequence does not build a property-style test covering "every resolver correctly handles `exists=False`" — if a future resolver gets retractions wrong, nothing in Steps 2–5 catches it.

## Steps

**Sequencing.** Done in order. Each step's landing informs re-planning of the next, so the sub-plans shouldn't be treated as frozen — expect Steps 3–5 to get re-read against what actually shipped upstream.

**Gate before Step 5's subscript flip.** Step 2's validator only constrains rows _written after_ it lands. Any pre-validator row missing a required key would KeyError on subscript access. Pre-launch the gate is cheap: Step 2 includes a post-merge wipe + re-ingest ([ProvenanceValidationTightening.md § Data posture](ProvenanceValidationTightening.md)). Step 5 must not land until that wipe has happened; if it was somehow skipped, a row audit is required first.

- **Step 1** — DONE (commit `e1d8886e`). `resolve_all_corporate_entity_locations` `exists=False` handling. See [LocationRetractionFix.md](LocationRetractionFix.md).
- **Step 2** — Provenance write-path validation tightening + registry unification. See [ProvenanceValidationTightening.md](ProvenanceValidationTightening.md).
- **Step 3** — Claim-value TypedDicts + resolver casts + consistency test. See [CatalogResolveTyping.md](CatalogResolveTyping.md).
- **Step 4** — Mypy baseline burn-down on `catalog/resolve/*` (helper annotations + tuple reuse cleanup). See [CatalogResolveBaselineCleanup.md](CatalogResolveBaselineCleanup.md).
- **Step 5** — Cleanup. Subscript flip on required keys ([ResolverReadsTightening.md](ResolverReadsTightening.md)) plus anything else surfaced while landing Steps 2–4.

Typing scope covered across Steps 3–4 (~44 mypy entries): `_relationships.py` (18), `_entities.py` (10), `__init__.py` (7), `_helpers.py` (5), `_media.py` (4). Downstream subscript-flip entries clear in Step 5.

## Relation to MypyFixing.md

[MypyFixing.md](MypyFixing.md) references this doc for the `catalog/resolve/*` work rather than owning it. Step numbering in sub-plans inherits from when this was Step 10 of MypyFixing.md — Step 2 was formerly 10.2, Steps 3–4 were carved out of 10.3, and Step 5 was formerly 10.4. The baseline reduction still counts against MypyFixing.md's scoreboard; what moved is the framing, not the measurement.
