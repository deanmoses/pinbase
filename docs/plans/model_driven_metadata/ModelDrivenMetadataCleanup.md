# Model-Driven Metadata Cleanup

Sibling doc to [ModelDrivenMetadata.md](ModelDrivenMetadata.md). The umbrella doc establishes the principle and the canonical Shape 1/2/3 templates. This doc covers the small-but-real gap between those templates and the existing codebase — typing inconsistencies, one fragile convention, and two hand-maintained lists that should be `_meta` walks.

## Scope

Bring existing model-driven metadata patterns to the canonical conventions in [ModelDrivenMetadata.md](ModelDrivenMetadata.md) before new spec work (`CatalogRelationshipSpec`, `CitationSourceSpec`) starts introducing more. Two motivations:

1. **Consistency as a copy-target.** Right now, a new contributor can copy `claim_fk_lookups` (untyped ad-hoc `getattr`) or `MEDIA_CATEGORIES` (`ClassVar`-typed, mixin-discovered) and propagate whichever inconsistency they happened to encounter. After this cleanup, any existing class attr is a valid template.
2. **Warm-up for the spec work.** The `AliasBase` upgrade and the Cluster 3 `_meta`-walk replacements exercise the same machinery (explicit identity attr, `ready()`-time discovery, parity tests) that `CatalogRelationshipSpec` needs — on a much smaller blast radius.

## Shape 2 typing sweep

Existing Shape 2 class attrs that work correctly but lack `ClassVar[...]` typing. Each is a one-line edit.

| Attr                            | Pre-sweep                     | Final                      |
| ------------------------------- | ----------------------------- | -------------------------- |
| `claim_fk_lookups`              | untyped, bare `getattr`       | `ClassVar[dict[str, str]]` |
| `claims_exempt`                 | untyped                       | `ClassVar[frozenset[str]]` |
| `soft_delete_cascade_relations` | untyped → `tuple[str, ...]`   | `ClassVar[frozenset[str]]` |
| `soft_delete_usage_blockers`    | untyped → `tuple[str, ...]`   | `ClassVar[frozenset[str]]` |
| `MEDIA_CATEGORIES`              | already `ClassVar[list[str]]` | unchanged                  |

The `soft_delete_*` attrs went through two commits: a first pass that mirrored the tuple literal on the RHS (`ClassVar[tuple[str, ...]]`), then a second pass that corrected the semantics to `ClassVar[frozenset[str]]` with a `frozenset({...})` RHS. History is preserved in the arrow above as a worked example of the rule below.

Rule of thumb for these annotations: pick the collection type that matches the **semantics** of the attr, not just what the RHS literal happens to look like. Order and duplicates are meaningless for `soft_delete_*` (they're unordered sets of relation names — same shape as `claims_exempt`), so `frozenset[str]` is the right annotation even if the RHS was originally written as a tuple literal. Update the RHS to `frozenset({...})` at the same time, and update any consumer `getattr(..., default)` defaults to match the annotated type (`frozenset()` here, not `()`) — don't lie about the shape in the annotation or smuggle a mismatched default past the type checker.

Consumer-side: the bare `getattr(model, "attr", default)` reads stay — they're the canonical Shape 2 access pattern per the umbrella. Only the declarations get typed.

### Declaration inventory (verified)

Confirmed by grep across `backend/apps/` before the sweep landed:

- `claim_fk_lookups` — `catalog/models/location.py` (1 site; `Location` only).
- `claims_exempt` — `catalog/models/location.py` (1 site; `Location` only).
- `soft_delete_cascade_relations` — `catalog/models/title.py` (1 site; `Title` only).
- `soft_delete_usage_blockers` — 5 sites across `catalog/models/`: `theme.py` (`Theme`), `taxonomy.py` (`RewardType`, `Tag`, `CreditRole`), `gameplay_feature.py` (`GameplayFeature`).
- `MEDIA_CATEGORIES` — base annotation on `MediaSupported` in `core/models.py`; concrete subclasses (`person`, `manufacturer`, `machine_model`, `gameplay_feature`) just assign values without re-annotating. This is the canonical "base annotates, subclasses assign" pattern and is the template `entity_type` should follow.

Every consumer uses `getattr(model_class, "attr", default)` with a default matching the annotated type — no shadowing, no drift risk. No base class declares any of the four opt-in attrs, so subclass declarations are the only source of truth.

### `entity_type` typing — separate sub-item

`entity_type` (LinkableModel's public identifier, listed in the umbrella as "already in the codebase") is also untyped today. It's Shape 2, same pattern, but has a bigger blast radius than the one-liners above: add `ClassVar[str]` to the base annotation on `LinkableModel`, then touch every concrete subclass assignment. Keep it as its own cleanup item rather than folding it into the table — the "one-line edit" framing doesn't fit. No consumer-side changes here either.

### Optional: `MEDIA_CATEGORIES` readiness validator

Not strictly required, but a `ready()`-time validator asserting every concrete `MediaSupported` subclass sets `MEDIA_CATEGORIES` to a non-empty list would catch "forgot to declare" errors at startup instead of first request. Defer if it adds friction; land if it's cheap.

## Shape 3 upgrades

### `AliasBase` — explicit identity attr

**Priority item — don't defer.** [ModelDrivenCatalogRelationshipMetadata.md](ModelDrivenCatalogRelationshipMetadata.md) puts alias models **out of scope** for `CatalogRelationshipSpec` because they're a separate axis with a different consumer shape. That's the correct architectural split, not a concession — but it does mean `_alias_registry.py` stays as the authoritative alias mechanism indefinitely, so the `verbose_name` derivation won't be swept up by any future spec work. This cleanup is how the fragility gets removed; nothing else will do it.

Currently `_alias_registry.py` derives the claim namespace from `_meta.verbose_name`:

```python
verbose_name = parent_model._meta.verbose_name
claim_field = f"{verbose_name.replace(' ', '_')}_alias"
```

This is the fragility flagged as "silver" in the Shape 3 ranking — changing a model's `verbose_name` silently changes the claim namespace. Upgrade:

1. Add an explicit class attr to each `AliasBase` subclass: `alias_claim_field: ClassVar[str] = "theme_alias"` (or whatever the current derived value is).
2. Update `discover_alias_types()` to read the explicit attr instead of deriving from `verbose_name`.
3. Add `apps.check_apps_ready()` at the top of `_build_map()` (currently relies on a docstring note).
4. Optional: add a `ready()`-time validator asserting every concrete `AliasBase` subclass declares the attr.

**Caveat.** `claim_field` strings may have runtime consumers beyond `_alias_registry.py` that parse or match on them. Grep before committing to this as a small change — the value might flow into claim keys, serializer output, or frontend code. If so, the upgrade is still correct (explicit > derived) but the blast radius is larger than one file.

### `core/entity_types.py` — cosmetic alignment

Currently uses a module-level `_ENTITY_TYPE_MAP: dict | None = None` with a `global` statement in `get_linkable_model()`. Already functionally gold. Swap to `@functools.lru_cache(maxsize=1)` on a build function to match the canonical template and `_alias_registry.py`. Purely cosmetic; skip if it reads as churn.

## Cluster 3 — `_meta`-walk replacements

Two hand-maintained lists that are one `_meta` / app-registry walk away from being derived. Both are Shape 1 (no spec, no class attr).

### Cache-invalidation signal list

Currently `catalog/signals.py` hand-lists eight models whose saves should bust the `/all/` cache. All eight are `CatalogModel` / `LinkableModel` subclasses plus two through-rows (`CorporateEntityLocation`, `Credit`). Upgrade: iterate the app registry at `ready()` time, filter to `CatalogModel` subclasses (plus any explicitly-marked through-models), connect signals in a loop. Parity test asserts the derived set matches the expected set for the current model landscape.

### `_SOURCE_FIELDS` in `citation/seeding.py`

Currently a hand-sync'd frozenset of scalar column names on `CitationSource`. Upgrade: derive from `CitationSource._meta.get_fields()` minus relations at seed time. Parity test catches drift if a scalar is added to the model but forgotten in seed YAML.

**Defer to `CitationSourceSpec` work.** This cleanup target overlaps the upcoming [ModelDrivenCitationSourceMetadata.md](ModelDrivenCitationSourceMetadata.md) axis, which will very likely subsume or reshape what `_SOURCE_FIELDS` describes. Landing it as a standalone `_meta`-walk now and then revisiting it under `CitationSourceSpec` means touching citation seeding twice. Skip until the citation spec work starts, then fold into that effort.

## Resolver signature standardization

Mechanical prep work for `CatalogRelationshipSpec` that has no dependency on the spec itself and reads cleanly as cleanup. See the "Resolver strategy" section of [ModelDrivenCatalogRelationshipMetadata.md](ModelDrivenCatalogRelationshipMetadata.md) for the full audit; the cleanup items are:

1. Rename `entity_ids` → `subject_ids` on all bespoke resolvers (affects `resolve_all_corporate_entity_locations`, `resolve_media_attachments`, and any others surfaced by the audit). Keep the existing `model_ids` callers working by renaming them too.
2. Drop the unused `dict[str, int]` stats return from `resolve_all_corporate_entity_locations` (no consumer reads it).
3. Confirm every bespoke resolver conforms to `(subject_ids: set[int] | None = None) -> None` after the above.

This is not _required_ before `CatalogRelationshipSpec` lands — the spec PR could do it — but separating it keeps the spec PR narrowly focused on introducing the spec + generic resolver, and lets the rename land sooner as an independent refactor.

## Sequencing

Rough ordering; not commit-level:

1. Shape 2 typing sweep (table) — fastest and lowest-risk, no behavior change.
2. `entity_type` typing — same pattern as (1) but bigger blast radius; natural follow-up.
3. Cache-invalidation signal list `_meta` walk — small, mechanical, proves out the parity-test pattern. (`_SOURCE_FIELDS` deferred to `CitationSourceSpec` work.)
4. `AliasBase` upgrade — priority; audit callers first, upgrade identity attr second, add readiness guard last.
5. Resolver signature standardization — independent cleanup; can land any time before `CatalogRelationshipSpec` implementation.
6. `entity_types.py` cosmetic — last, optional.

None of these have hard dependencies on the new spec work. They can land before or alongside it; the value is that new-spec contributors have a clean, consistent landscape to copy from.
