# Claims Exempt

## Status: DONE

Landed in PR #281 (`refactor/model-driven-claims-metadata`). No follow-up work remains in this doc's scope.

## Context

This work is part of the family described in [ModelDrivenClaimsMetadata.md](ModelDrivenClaimsMetadata.md), and an instance of the broader pattern in [ModelDrivenMetadata.md](ModelDrivenMetadata.md): encode per-model behavior on the model itself, consume it generically from shared infrastructure.

`claims_exempt` is the per-model knob that excludes specific fields from claim control entirely. The fields named here keep whatever Django shape they have on the row but aren't discovered, materialized, or validated by the claims layer.

## The contract

`ClaimControlledModel` declares:

```python
claims_exempt: ClassVar[frozenset[str]] = frozenset()
```

Default empty — every existing model is unaffected. Location declares:

```python
claims_exempt: ClassVar[frozenset[str]] = frozenset({"location_path"})
```

`location_path` is materialized from `parent` + `slug` at create time, never edited afterward, and never carries a claim. Listing it in `claims_exempt` keeps `get_claim_fields` from treating it as a claim-controlled field.

`get_claim_fields(model_class)` in `apps/provenance/models/introspection.py` reads `model_class.claims_exempt` to filter the discovered claim fields. Downstream consumers (resolvers, validators, the claim executor) see only the filtered set; nothing else needs to know about exemption.

## Landed state

This hoist landed in PR #281. `claims_exempt` is now the contract on `ClaimControlledModel`, not an ad-hoc subclass attr discovered by consumer-side `getattr`.

What changed:

- `ClaimControlledModel` declares `claims_exempt: ClassVar[frozenset[str]] = frozenset()`.
- Subclass declarations remain as overrides of the base default.
- `get_claim_fields()` accepts `type[ClaimControlledModel]` and reads `model_class.claims_exempt` directly.
- `get_claim_fields()` now lives in `apps.provenance.models.introspection`, with a public re-export from `apps.provenance.models`.
- Runtime behavior is unchanged: exempt fields are simply omitted from the claim-controlled field set.

## Why this lives on `ClaimControlledModel`

The set of fields exempt from claim control is meaningful only for models that participate in claim control. `ClaimControlledModel` is the smallest base that captures the audience. Hoisting puts the contract on the class the consumer already knows about, lets the type checker enforce the shape, and makes a fourth or fifth ClassVar in this family (see [ModelDrivenClaimsMetadata.md](ModelDrivenClaimsMetadata.md)) cheap to add — same shape, same home, same hoist recipe.
