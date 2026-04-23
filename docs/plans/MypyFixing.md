# Mypy Fixing

The mypy baseline (`backend/mypy-baseline.txt`) has 710 entries. ~82% are three error classes:

- `no-untyped-def` — 337
- `type-arg` — 128 (bare `dict` / `list` / `set`)
- `no-untyped-call` — 114 (caller penalized because the callee is untyped)

Hotspots are concentrated: `apps/catalog/api/*` dominates, followed by `catalog/management/commands/ingest_pinbase.py` (47), `citation/api.py` (38), and `catalog/ingestion/opdb/adapter.py` (30). Fix patterns, not baseline lines.

## Running mypy

- **Full check:** `./scripts/mypy` from the repo root. Wraps `uv run --directory backend mypy --config-file pyproject.toml .` piped through `mypy-baseline filter`. Exit 0 only when no _new_ (above-baseline) errors exist. Reports `fixed / new / unresolved` and a per-error-code breakdown with deltas. Do **not** run `mypy` directly — absolute paths won't match the baseline.
- **Don't pass a file path.** `./scripts/mypy src/foo.py` is ignored by the wrapper on purpose (see the comment at the top of [scripts/mypy](scripts/mypy)); partial runs generate paths that don't align with the baseline.
- **Sync baseline after clearing entries:** `uv run --directory backend mypy --config-file pyproject.toml . 2>&1 | uv run --directory backend mypy-baseline sync`. Only run this once `./scripts/mypy` shows `new: 0`.
- **Kill dmypy when the type system changes.** `scripts/mypy` uses fresh one-shot mypy, but the IDE and `scripts/dmypy` use a persistent daemon. Adding a type alias, changing an override, or renaming a module-level symbol can make dmypy's cache stale and report wrong errors. Fix: `uv run --directory backend dmypy stop` (the IDE pays cold-start cost on next check).
- **Relevant overrides to keep in mind** (from [backend/pyproject.toml](backend/pyproject.toml)):
  - `strict = true` is global. Touching imports in an otherwise-clean file can surface new errors.
  - `*.tests.*` / `conftest` relaxes `disallow_untyped_defs` + friends ([line 127](backend/pyproject.toml#L127)) — annotation-style rules only, not `arg-type` / `attr-defined` / etc.
  - `apps.*.api.*` relaxes `disallow_untyped_decorators` ([line 136](backend/pyproject.toml#L136)) for Ninja's untyped decorators.

## Guiding principles

- **Type callees before callers.** Most `no-untyped-call` errors evaporate when the function being called gets annotated. Sweeping caller signatures against `Any`-returning helpers just means revisiting them.
- **Ratchet via the baseline, not per-module strictness.** `strict = true` is already global in [backend/pyproject.toml](backend/pyproject.toml); the only per-module levers are _relaxations_, and the enforceable direction is removing them. Concretely: (a) shrink `mypy-baseline.txt` monotonically and fail CI on new entries (`mypy-baseline --fail-on-new-error` or equivalent); (b) as `apps.*.api.*` packages clean up, narrow or remove the `disallow_untyped_decorators = false` relaxation at [pyproject.toml:136](backend/pyproject.toml#L136).
- **Re-run `make api-gen` after any Ninja endpoint retyping.** Annotated return types change the generated OpenAPI schema and therefore `frontend/src/lib/api/schema.d.ts`. Run the frontend typecheck too, not just pytest.

## Idiom for serialization helpers: return Schema, not `dict`

In a Django + Ninja app, the Ninja `Schema` (Pydantic v2) is the canonical data shape — for request/response validation _and_ for in-process typing. Serialization helpers should **return Schema instances**, not dicts that later get re-validated against the same Schema.

- **Schema-shaped output → return the Schema instance.** Pydantic v2 construction is microseconds; the "runtime cost" concern is not real.
- **No Schema exists yet for this shape → add one.** Two duplicated shapes (a TypedDict and a Schema) is a worse outcome than one Schema used everywhere.
- **Truly free-form `JSONField` bags → `JsonData` from [apps/core/types.py](backend/apps/core/types.py).** Only `extra_data` qualifies. `JsonData = Mapping[str, object]` — `object` (not `Any`) forces `isinstance`-narrowing at use sites, which is correct for JSON. `Mapping` (covariant) is needed because dict literals with specific value types aren't subtypes of the invariant `dict[str, object]`. Use `JsonBody` (the `dict` form) only for test-client write bodies.
- **Exception: cached-bytes hot paths.** Endpoints that build the input to `set_cached_response` (e.g. `list_all_titles`, `list_all_models`) persist JSON bytes; the dict _is_ the cached form. Building Schemas only to `model_dump()` them back is the round-trip the cache exists to avoid. Keep these few helpers dict-returning, type the local as `list[dict[str, Any]]`, and leave a comment naming the cache contract. The Schema for the same shape still applies to the non-cached sibling endpoint.

`TypedDict` is the fallback for code that can't or won't use Pydantic. In a Ninja app, Pydantic is already present — use it.

## Idiom for `Any`: four categories, only one is valid

Writing `Any` means "don't type-check this." Default to never. When tempted, classify which of these it is:

1. **Lazy `Any`** — "I haven't bothered to write the real type." The real type exists and callers pass exactly it. **Not valid.** Write the real type.
2. **Queryset-annotated attribute** — a single `.annotate()` field (e.g. `title.model_count`) that isn't on the model. Typing the param as `Any` throws away the whole model's type info to paper over one attribute. **Not valid.** Use `getattr(obj, "annotated_field", default)` — scoped to the one field.
3. **Third-party API constraint that forces information loss** — e.g. `Prefetch[str, Any, str]` on a factory feeding `prefetch_related`, which has a single `_PrefetchedQuerySetT` TypeVar that can't unify across heterogeneous concrete args. The `Any` isn't hiding info we have; it acknowledges the 3rd-party API shape discards it. **Valid — with a comment naming the constraint.**
4. **"JSON-shaped" data** — looks like it justifies `Any` but doesn't; JSON's value type is `object` with `isinstance`-narrowing. **Not valid.** Use `JsonData` / `JsonBody`.

Rule: if you're about to write `Any` and it's not #3, find the real type.

## Idioms for introspection-heavy code

For code that operates on a generic `type[Model]` (resolvers, validators, management commands):

- **Use `_default_manager` instead of `.objects`** — typed on the base `Model` class; `.objects` is added per-subclass and invisible at `type[Model]`.
- **Narrow `type[Model] | Literal['self']`** with `assert isinstance(target_model, type) and issubclass(target_model, models.Model)`. At runtime `"self"` is already resolved by `_meta.get_field()`; the union is a django-stubs artifact.
- **Narrow `Field | ForeignObjectRel`** with `isinstance(field, models.Field)`. `ForeignObjectRel` lacks `validators`, `blank`, `to_python`, `choices`.

## Idiom for generics over heterogeneous model classes

When a helper is generic over N concrete model classes that share a Schema shape but _don't_ share a base class carrying the fields / custom manager (e.g. the 9 taxonomy models share `name` / `slug` / `display_order` / `CatalogManager` but inherit them from different mixins):

- **Constrained `TypeVar`, not bound.** A bound TypeVar (`[M: CatalogModel]`) collapses `type[M]` to the common base and loses `.objects.active()` and the per-subclass fields. Only a constraint list preserves the concrete type at each call site.
- **`typing.TypeVar` with a module-level constraint list + per-def `# noqa: UP047`.** PEP 695 inline syntax (`def foo[M: (A, B, C, …)](…)`) is ergonomic for 1–2 constraints but forces the full list to be repeated at every generic function. Module-level `TypeVar` keeps the constraints DRY; ruff's UP047 then fires per def — suppress it locally.
- **Narrow with `isinstance`, not `hasattr` + `getattr`.** When one arm of the union has a reverse relation the others don't (e.g. only `RewardType` has `aliases`), `if isinstance(obj, RewardType): obj.aliases.all()` type-checks cleanly. The `hasattr` + `getattr(obj, "attr")` spelling trips ruff's B009.
- **The speculative fix is a shared abstract base.** Introducing a `TaxonomyBase` mixin with the shared fields and manager would let a bound TypeVar work and eliminate the noqas. Not in-scope for any step of this plan — revisit only if multiple future helpers need the same shape or the entity-type registry consolidation lands.

## Idiom for Schema/dict boundaries during migration

When a helper transitions from returning `dict` to returning `Schema`, but the converse boundary still returns `dict` — either a shared callback registrar consumed by untyped callers, or a cross-step callee whose own conversion is scheduled later:

- **Wrap at the boundary, not the callee.**
  - Schema-side calling dict-side: `Schema.model_validate(callee_dict(...))` at the call site. (Step 1 titles.py → step 2 machine_models.py used this for `MachineModelDetailSchema.model_validate(_serialize_model_detail(pm))`.)
  - Dict-side calling Schema-side: `serialize_detail=lambda obj: _serialize_taxonomy(obj).model_dump()` confines the round-trip to the single call site.
  - Either way, tightening the shared callback type or callee return ripples into every untyped consumer, ballooning the current step's scope.
- **Flag the wrapper as tech debt.** A comment naming the later step that will remove the bridge keeps the intent visible. Don't silently leave the `.model_dump()` / `.model_validate()` hop in place once the boundary is tightened.

## Idiom for narrowing optional FK fields

`obj.fk_id is not None` (column read, no DB hit) and `obj.fk is not None` (related-object dereference, may hit the DB) **are not equivalent**. Don't swap one for the other to satisfy mypy.

- The original guard is usually `obj.fk_id is not None` because callers don't want the related fetch.
- To narrow the related object for mypy without changing semantics, bind a local and assert: `parent = obj.fk; assert parent is not None`. The `_id` check guarantees the assert holds; the local lets mypy track the narrowing through the rest of the block.

## Step 1 — Keystone helpers in `catalog/api`

Type the shared helpers before their callers. Expect the `no-untyped-call` count to drop noticeably as a side effect.

- [apps/catalog/api/taxonomy.py](backend/apps/catalog/api/taxonomy.py) — **done** (58 → 2; the 2 remaining are pre-existing `Cannot infer type of lambda` on default-arg-captured lambdas in the `_register_*` wrappers).
- [apps/catalog/api/titles.py](backend/apps/catalog/api/titles.py) — **done** (51 → 0). Two `MachineModelDetailSchema.model_validate(_serialize_model_detail(...))` bridges remain; remove when step 2 converts `_serialize_model_detail` to return the Schema. `_serialize_model_detail` and `_model_detail_qs` in [machine_models.py](backend/apps/catalog/api/machine_models.py) were minimally typed (return `dict[str, Any]` and `QuerySet[MachineModel]`) as cross-file callee unblocks — the full Schema conversion is step 2 work.

Return Schema instances (see idiom above). Add schemas for shapes that don't have one yet.

## Step 2 — rest of `catalog/api`

With taxonomy + titles done, the rest of the package falls into two groups. Order matters: shared-helper modules first (callee-before-caller), then endpoint-only files. Run `make api-gen` + frontend typecheck after each batch.

**2a — shared helpers** (not endpoint files; expose the keystone helpers every endpoint in the package calls — `execute_claims`, `plan_*`, `assert_*`, `serialize_blocking_referrer`, `execute_soft_delete`):

`edit_claims.py` (17) → `soft_delete.py` (17) → `entity_create.py` (11) → `entity_crud.py` (17).

Typing these first means the 2b sweep collects `no-untyped-call` reductions for free.

**2b — endpoint signatures** (`request: HttpRequest`, explicit Schema return types):

`systems.py` (12) → `manufacturers.py` (11) → `series.py` (10) → `locations.py` (20) → `people.py` (20) → `machine_models.py` (34) → `page_endpoints.py` (46).

`machine_models.py` is sequenced before `page_endpoints.py` for two reasons: (a) it carries the titles.py → step-2 bridges (`MachineModelDetailSchema.model_validate(_serialize_model_detail(...))`) which step 2 should remove, not perpetuate; (b) `page_endpoints.py` imports `_serialize_model_detail` / `_model_detail_qs` from it, so typing machine_models first unblocks the largest file the same way it unblocked titles.

**Land a shared `ErrorDetailSchema` during 2b.** Almost every endpoint file declares `response={..., 422: dict, 404: dict}` with bodies like `{"detail": "..."}` or `{"detail": "...", "blocked_by": [...]}`. Define `ErrorDetailSchema` and `SoftDeleteBlockedSchema` once, replace the `dict` declarations as each file is swept. Cheaper to do during the same touch than to revisit; also removes the lazy-`Any` placeholders that titles.py left behind (`422: dict[str, Any]`, etc.).

When the package is clean, shrink `mypy-baseline.txt` to drop its entries and (if feasible) narrow the `apps.*.api.*` decorator relaxation.

## Step 3 — `citation/api` and `provenance/api`

Same pattern — helpers first, endpoints after, `make api-gen` between batches. Smaller scopes (38 + 15 entries); should go quickly after step 2's muscle memory.

## Step 4 — `catalog/resolve/*`

Refactor tuple-heavy resolver code into `dataclass` / `TypedDict` where state is being unpacked inconsistently. Apply the idioms above for remaining `attr-defined` / `union-attr` noise.

## Step 5 — Ingestion and management commands

Grouped because they share patterns (external I/O, command runners, bare dicts from JSON parsing):

- [catalog/management/commands/ingest_pinbase.py](backend/apps/catalog/management/commands/ingest_pinbase.py) (47 — #2 hotspot)
- [catalog/ingestion/opdb/adapter.py](backend/apps/catalog/ingestion/opdb/adapter.py) (30)
- [catalog/ingestion/ipdb/adapter.py](backend/apps/catalog/ingestion/ipdb/adapter.py) (20)
- [catalog/management/commands/validate_catalog.py](backend/apps/catalog/management/commands/validate_catalog.py) (17)
- remaining ingestion + media tail

## Process

- `strict = true` is already global, so the enforcement surface is the baseline itself plus removing relaxations.
- Fail CI on new baseline entries and shrink the file monotonically as each step lands.
- As `apps.*.api.*` cleans up, narrow or remove the `disallow_untyped_decorators = false` relaxation at [pyproject.toml:136](backend/pyproject.toml#L136).
