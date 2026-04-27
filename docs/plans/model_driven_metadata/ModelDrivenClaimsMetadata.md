# Model-Driven Claims Metadata

## Status: partially landed

The `claims_exempt` and `claim_fk_lookups` pieces landed in PR #281 (`refactor/model-driven-claims-metadata`). The branch:

- moved `get_claim_fields()` from `apps.core.models` to `apps.provenance.models.introspection`, re-exported as `apps.provenance.models.get_claim_fields`;
- declared `claims_exempt` and `claim_fk_lookups` on `ClaimControlledModel` with typed empty defaults;
- narrowed the claims chain from `type[Model]` to `type[ClaimControlledModel]` where the code is operating on a claim subject's model class;
- replaced `getattr(..., default)` reads of those ClassVars with direct attribute access.

`immutable_after_create` remains planned.

A small family of `ClassVar`s on `ClaimControlledModel` that customize per-model behavior of the claims layer. Each landed member is declared on the base with an empty default and overridden where needed by subclasses; each is consumed generically by claim infrastructure (no `isinstance` checks anywhere downstream).

This is one facet of the broader goal in [ModelDrivenMetadata.md](ModelDrivenMetadata.md): encode per-model behavior on the model itself, consumed generically by shared infrastructure. See the umbrella for the underlying pattern ([base class / mixin](ModelDrivenMetadata.md#pattern-base-class--mixin)) and the antipattern ([field-on-model](ModelDrivenMetadata.md#antipattern-field-on-model)) this family of work fixes.

## The ClassVars

Each item is its own piece of work — typing, hoist to the base, consumer cleanup, tests — and gets its own doc.

- **`claims_exempt`** — which fields are excluded from claim control. Default `frozenset()`. See [ModelDrivenClaimsExemptMetadata.md](ModelDrivenClaimsExemptMetadata.md).
- **`claim_fk_lookups`** — per-FK override of the lookup field used in claim writes and resolution. Default `{}`. See [ModelDrivenClaimFkLookupsMetadata.md](ModelDrivenClaimFkLookupsMetadata.md).
- **`immutable_after_create`** — which fields, once set, cannot change. Planned default `frozenset()`. See [ModelDrivenImmutableAfterCreate.md](ModelDrivenImmutableAfterCreate.md).
