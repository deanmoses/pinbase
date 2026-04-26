# Type API Error Responses

## Context

The Django Ninja contract is silent on the failure path. Roughly 80%
of mutating endpoints declare `response={200: …}` only; 4xx bodies
are produced by global exception handlers in
[backend/config/api.py:89-111](../../../../backend/config/api.py)
that the OpenAPI doc never sees. The frontend's
[parse-api-error.ts](../../../../frontend/src/lib/api/parse-api-error.ts)
handles three runtime shapes — clear evidence the contract isn't
pinned.

Runtime is already correct. This is a contract-honesty fix. The
goal: document the _interesting_ failure modes — those with custom
shapes a contract reader can't guess — and reduce the frontend
parser's branching at the same time.

**Who actually consumes this work.** Today's audience is the
TypeScript checker (catches frontend regressions when wire shapes
change), the [parse-api-error.ts](../../../../frontend/src/lib/api/parse-api-error.ts)
maintainer, and humans / AI reading `/api/docs`. There is no second
API client. The plan is worth doing for parser simplification (three
runtime branches → two) and for making the OpenAPI doc reflect
runtime truth; broader downstream-consumer benefits are
hypothetical and not the justification.

The plan does this in two moves: declare custom 4xx shapes per
endpoint where they originate, and override Ninja's built-in
malformed-body 422 to share the application's structured-422
envelope so the frontend has one fewer shape to parse. Stock 4xx
(`{detail: string}` for 400/401/403/404) is left undeclared because
every contract reader already knows that shape.

The global exception handlers stay. They're the runtime source of
truth for `StructuredValidationError` and `RateLimitExceededError`
and they catch transitively-raised errors from anywhere in the call
stack — a guarantee no per-endpoint pattern provides.

## The 422 / 429 landscape today

Verified by grep across `apps/`:

**422 has three live shapes:**

1. **Structured validation** — `{detail: {message, field_errors,
form_errors}}` from `StructuredValidationError`, used by every
   catalog mutating endpoint via `execute_claims`. Also what Ninja's
   built-in malformed-body validation will produce after §2's
   override.
2. **Plain detail** — `{detail: string}` from
   `raise HttpError(422, "msg")`. Used in
   [citation/api.py](../../../../backend/apps/citation/api.py) (8
   raises) and [provenance/api.py](../../../../backend/apps/provenance/api.py)
   (5 raises). Restore endpoints in
   [entity_crud.py:208,215](../../../../backend/apps/catalog/api/entity_crud.py)
   explicitly return `(422, ErrorDetailSchema(...))`.
3. **Delete-specific richer** — `SoftDeleteBlockedSchema |
AlreadyDeletedSchema` at
   [entity_crud.py:194](../../../../backend/apps/catalog/api/entity_crud.py).
   Drives the frontend's delete-flow classifier and stays as-is.

**429 has two live shapes:**

1. **Structured rate-limit** — `{detail: {message, bucket,
retry_after}}` from `RateLimitExceededError` via the
   `check_and_record` helper.
2. **Plain detail** — `{detail: string}` from
   `raise HttpError(429, "Upload limit exceeded.")` at
   [media/api.py:76](../../../../backend/apps/media/api.py).

The plan does **not** unify 422 or 429 across these shapes. It
unifies the structured paths (Ninja's built-in 422 joins
`StructuredValidationError`'s envelope; the rate-limit handler is
already singular) and lets plain-detail raises continue to use
`ErrorDetailSchema`. Per-endpoint declarations document which shape
each endpoint actually produces.

## Decisions

1. **Two new schemas for the structured shapes.**
   `ValidationErrorSchema` for structured 422;
   `RateLimitErrorSchema` for structured 429. Both have custom
   shapes a reader can't guess and warrant contract documentation.

2. **Override Ninja's built-in `ValidationError` to produce
   `ValidationErrorSchema`.** Today, malformed request bodies
   produce `{detail: [{loc, msg}, …]}` — a third wire shape the
   frontend parser handles. A global override reshapes this into
   the same envelope `StructuredValidationError` produces. One
   wire shape for _validation_ 422s; frontend parser drops to two
   runtime branches.

3. **Keep the global `StructuredValidationError` and
   `RateLimitExceededError` handlers.** They're the runtime safety
   net for raises that originate deep in the call stack. The
   guiding principle: explicit `return (code, body)` from view
   bodies belongs where the failure shape is endpoint-local and
   the body is computed in-view (e.g. delete's `blocked_by` list);
   global handlers belong where the raise originates deep in the
   call stack and the body is generic across endpoints.

4. **Plain-detail 4xx raises continue to use `ErrorDetailSchema`.**
   `HttpError(422, "msg")`, `HttpError(429, "msg")`, and explicit
   `(code, ErrorDetailSchema(...))` returns all produce
   `{detail: string}` and get declared as `<code>: ErrorDetailSchema`.

5. **No sweep of 400 / 401 / 403 / 404.** Stock Ninja
   `{detail: string}`; the OpenAPI doc gains nothing by repeating
   it on every endpoint.

6. **Sweep all mutating endpoints that produce 422 or 429.** A
   partial sweep would leave the contract half-honest in a way
   that's worse than fully silent.

7. **No new invariant tests.** Static-analysis or
   runtime-instrumentation tests to catch missing declarations
   were considered and rejected. Code review on this PR is the
   enforcement; the broader Boundary-tests task can pin the
   convention later if needed.

## Wire-shape compatibility

§2 changes Ninja's stock malformed-body 422 from
`{detail: [{loc, msg}, …]}` to
`{detail: {message, field_errors, form_errors}}`. This is a
deliberate behavioral change to a documented framework default,
not just a contract annotation.

It's acceptable because Pinbase has one API client (the SvelteKit
frontend), updated in this same PR. **Pinbase deploys as a single
container** ([docs/Hosting.md](../../../../docs/Hosting.md): Caddy

- Django + SvelteKit in one Railway service), so backend and
  frontend land atomically — no split-deploy window where the new
  backend serves the new shape to a deployed-old frontend that
  expects the array shape.

The override uses Ninja's officially supported extension point
(`@api.exception_handler(ValidationError)`), not framework
internals.

## Approach

### 1. Add the schemas

Edit [backend/apps/core/schemas.py](../../../../backend/apps/core/schemas.py):

- `ValidationErrorBodySchema` — `{message: str, field_errors: dict[str, str], form_errors: list[str]}`. Mirrors the `StructuredErrorBody` TypedDict at [edit_claims.py:68](../../../../backend/apps/catalog/api/edit_claims.py).
- `ValidationErrorSchema` — `{detail: ValidationErrorBodySchema}`.
- `RateLimitErrorBodySchema` — `{message: str, bucket: str, retry_after: int}`.
- `RateLimitErrorSchema` — `{detail: RateLimitErrorBodySchema}`.

Keep `ErrorDetailSchema` and the `StructuredErrorBody` TypedDict
as they are.

### 2. Override Ninja's built-in `ValidationError`

Two edits to [backend/config/api.py](../../../../backend/config/api.py):

**(a) Extract a helper for the structured-422 dict.** Today the
existing handler delegates to `exc.to_response_body()` and the new
override would hand-write the same shape. A single helper
consolidates both:

```python
def _structured_422_body(
    *, message: str, field_errors: dict[str, str], form_errors: list[str]
) -> dict[str, object]:
    return {
        "detail": {
            "message": message,
            "field_errors": field_errors,
            "form_errors": form_errors,
        }
    }
```

Update the existing `_handle_structured_validation_error` to call
the helper. Drift surface narrows to two definitions — the helper
and `ValidationErrorBodySchema`.

**(b) Add the `ValidationError` override:**

```python
from ninja.errors import ValidationError

@api.exception_handler(ValidationError)
def handle_pydantic_validation(request, exc):
    field_errors: dict[str, str] = {}
    form_errors: list[str] = []
    for err in exc.errors:
        loc = err.get("loc") or ()
        msg = err.get("msg", "Invalid value.")
        # Use the last loc segment as the field key. Pinbase's per-field
        # error renderer keys on bare names ("year", "slug") — matching
        # what application-thrown StructuredValidationError uses. Loc
        # paths from Pydantic include request source + nesting
        # ("body", "gameplay_features", 0, "slug"); collapsing to the
        # leaf preserves UI compatibility. Trade-off: leaf-name collisions
        # in nested payloads (two fields named "slug") map to the same
        # key. Acceptable because malformed-body errors are programmer
        # bugs, not user-facing field corrections; the inline-render
        # path that *does* care about per-field accuracy is fed by
        # StructuredValidationError, which produces flat keys directly.
        leaf = str(loc[-1]) if loc else ""
        if leaf and leaf not in {"body", "query", "path", "header", "cookie", "form"}:
            field_errors[leaf] = msg
        else:
            form_errors.append(msg)
    return JsonResponse(
        _structured_422_body(
            message="Invalid request.",
            field_errors=field_errors,
            form_errors=form_errors,
        ),
        status=422,
    )
```

Notes:

- **Field-key strategy: `loc[-1]`, not dotted paths.** Verified
  against Pinbase payloads: `ModelClaimPatchSchema` and friends
  contain nested fields (`gameplay_features: list[GameplayFeatureInput]`,
  `fields: dict[str, Any]`). A dotted path like
  `"gameplay_features.0.slug"` would not match the frontend's
  per-field renderer keys, which today expect flat names like
  `"slug"`. Using `loc[-1]` matches existing UX. The collision
  trade-off is documented in the inline comment.
- **The fallback to `form_errors`** when the leaf is a request
  source (`body`/`query`/etc., e.g. for "missing body" errors with
  `loc=("body",)`) keeps top-level errors out of `field_errors`.
- **Static `"Invalid request."` message** is deliberate. The
  frontend's parser builds toast text by joining `form_errors` and
  `Object.entries(field_errors).map(...)`, so the top-level
  `message` field is rarely user-facing. Building a richer summary
  from Pydantic's `msg` strings would duplicate logic the frontend
  already does and add string-parsing brittleness; the static
  message keeps the schema simple.
- **`JsonResponse` over `api.create_response`** matches the
  existing handler style in this file. Switching to
  `create_response` (which routes through Ninja's renderer) is
  out of scope; if Ninja's content negotiation ever matters,
  migrate both handlers together.
- The existing `StructuredValidationError` and
  `RateLimitExceededError` handlers stay (with the helper update
  in (a)).

**Add a unit test** that exercises a deeply-nested malformed body
against an endpoint using `ModelClaimPatchSchema` (e.g. invalid
type for `gameplay_features[0].count`) and confirms the `loc[-1]`
mapping puts the error under a recognizable field key. Lock the
behavior in before the sweep.

### 3. Sweep mutating endpoint declarations

Per-endpoint, expand `response={…}` based on what the function
body (and the helpers it calls one level deep) can raise.

**Status-code-first rules:**

- **422 structured** (`ValidationErrorSchema`): endpoint calls
  `execute_claims`, or any helper that can raise
  `StructuredValidationError` (`validate_name`,
  `validate_slug_format`, `assert_name_available`,
  `create_entity_with_claims`).
- **422 plain** (`ErrorDetailSchema`): endpoint raises
  `HttpError(422, "msg")` directly, or returns
  `(422, ErrorDetailSchema(...))` explicitly.
- **422 union** (`ErrorDetailSchema | ValidationErrorSchema`):
  endpoint can produce both shapes. Verified by grep across the
  in-scope files: no current endpoint does this. The rule is
  theoretical; if the sweep surfaces one, declare the union.
- **429 structured** (`RateLimitErrorSchema`): endpoint calls
  `check_and_record`.
- **429 plain** (`ErrorDetailSchema`): endpoint raises
  `HttpError(429, "msg")` directly. Currently only
  [media/api.py:76](../../../../backend/apps/media/api.py).

Read each view carefully and apply the rule that fits. Don't
over-declare to be safe — `response={200: Foo, 422: ValidationErrorSchema}`
on an endpoint that can't produce 422 lies to contract readers.
If a classification is non-obvious, note it in the PR
description.

**Sweep targets**, grouped by what each file currently produces:

**Generator-built endpoints — both generators live in
[entity_crud.py](../../../../backend/apps/catalog/api/entity_crud.py):**

- `register_entity_delete_restore` ([entity_crud.py:72](../../../../backend/apps/catalog/api/entity_crud.py))
  — delete already declares `422: SoftDeleteBlockedSchema |
AlreadyDeletedSchema`; restore already declares
  `422: ErrorDetailSchema`. **Leave both as-is.**
- `register_entity_create` ([entity_crud.py:243](../../../../backend/apps/catalog/api/entity_crud.py))
  — current declarations are `response={201: response_schema}`
  only. Add `422: ValidationErrorSchema`. Propagates to series,
  corporate_entities, franchises, themes, manufacturers,
  gameplay_features, taxonomy, systems creates built through
  this generator.

`entity_create.py` is helper code only (`validate_*`,
`assert_*`, `create_entity_with_claims`) — no routes, no
declarations to change.

**Bespoke catalog endpoints (structured 422 via `execute_claims`)
→ add `422: ValidationErrorSchema`:**

- [titles.py](../../../../backend/apps/catalog/api/titles.py) (3 mutating views)
- [people.py](../../../../backend/apps/catalog/api/people.py) (3)
- [machine_models.py](../../../../backend/apps/catalog/api/machine_models.py) (3)
- [systems.py](../../../../backend/apps/catalog/api/systems.py) (1 bespoke create; delete/restore inherit from the generator)

**Bespoke endpoints with plain `HttpError(422, …)` raises → add
`422: ErrorDetailSchema`:**

- [citation/api.py](../../../../backend/apps/citation/api.py)
  (8 raise sites — lines 267, 273, 274, 444, 511, 519, 589, 654).
- [provenance/api.py](../../../../backend/apps/provenance/api.py)
  — already declares `422: ErrorDetailSchema` on lines 174, 220,
  303, 350. Verified (grep): zero `StructuredValidationError`
  raises and zero `execute_claims` calls. Audit and add
  `422: ErrorDetailSchema` to any mutating endpoint that raises
  but doesn't yet declare it. **Do not swap any existing
  `ErrorDetailSchema` to `ValidationErrorSchema`** — provenance
  produces only plain bodies.

**Endpoints that produce 429:**

- [media/api.py:76](../../../../backend/apps/media/api.py) raises
  `HttpError(429, …)` → add `429: ErrorDetailSchema` to the
  upload endpoint.
- Any endpoint that calls `check_and_record` → add
  `429: RateLimitErrorSchema`. Audit
  [provenance/rate_limits.py](../../../../backend/apps/provenance/rate_limits.py)
  call sites.

**Endpoints with no 422 or 429 surface** (per grep):
[media/api.py](../../../../backend/apps/media/api.py) mutating
endpoints other than line 76 (raise 400/404/500 only — out of
scope) and [accounts/api.py](../../../../backend/apps/accounts/api.py)
(no 422/429 raises). Skip.

### 4. Regenerate types and simplify the frontend parser

Run `make api-gen` to regenerate
[frontend/src/lib/api/schema.d.ts](../../../../frontend/src/lib/api/schema.d.ts).
The generated file gains `ValidationErrorSchema`,
`ValidationErrorBodySchema`, `RateLimitErrorSchema`, and
`RateLimitErrorBodySchema` under `components.schemas`.

Rewrite [parse-api-error.ts](../../../../frontend/src/lib/api/parse-api-error.ts):

- Public signature `parseApiError(error: unknown): {message, fieldErrors}`
  unchanged — callers across the frontend need no edits.
- **Two runtime branches** (down from three):
  1. **`ValidationErrorSchema`** — structured 422.
     `{detail: {message, field_errors, form_errors}}`. Now
     produced by both endpoint-local 422s and Ninja's built-in
     malformed-body 422 (per §2).
  2. **`ErrorDetailSchema`** — `{detail: string}`. Stock Ninja
     shape: 401, plain `HttpError(400|403|404|409|422|429, …)`
     raises, CSRF/405, middleware errors. 422 and 429 can arrive
     in _either_ envelope; the parser dispatches by body shape,
     not by status.
- The Pydantic-array branch is **deleted**. After §2 lands, no
  code path in the API produces it.
- Final fallback for genuinely unexpected shapes:
  `{message: JSON.stringify(error), fieldErrors: {}}`.

Import path note: if the re-export barrel from the broader
API-boundary work has landed at `$lib/api/types`, import schema
types from there; otherwise use the indexed-access form
`components['schemas']['ValidationErrorSchema']`.

Update [parse-api-error.test.ts](../../../../frontend/src/lib/api/parse-api-error.test.ts):

- Add a test asserting that a malformed-body 422 (the kind Ninja
  used to produce as an array) now arrives as
  `ValidationErrorSchema` after the override.
- **Keep one Pydantic-array test case** that asserts the parser
  falls through gracefully to the unknown-shape fallback. Defensive
  coverage in case a future Ninja upgrade reintroduces the array
  shape through a path the override doesn't intercept.
- Cover both branches plus the unknown-shape fallback.

## Out of scope

- **Sweep of 400 / 401 / 403 / 404 declarations.** Stock Ninja
  shape; not worth the verbosity.
- **Authenticated GET endpoints.** Read paths are silent on 4xx
  today and can stay that way.
- **Converting raises to explicit `Status[…]` returns** at the
  view boundary. Considered and rejected: Ninja's response-map
  validation is runtime, not compile-time, so the conversion would
  add ~30 `try/except` blocks without delivering a structural
  drift-prevention guarantee.
- **An invariant test** that asserts every endpoint raising X
  declares X. Deferred to the broader Boundary-tests task.
- **Renaming `…Schema` suffix off the new schemas.** Lands under
  existing naming convention; renames happen in the broader
  rename pass.
- **Unifying plain `HttpError(422|429, "msg")` raises into the
  structured schemas.** Would require touching every raise site
  to construct the structured body, and the resulting body
  (`{message: "msg", field_errors: {}, form_errors: []}`) is
  awkward — these errors don't have field context.
- **Migrating handlers from `JsonResponse` to
  `api.create_response`.** Not needed today; revisit if Ninja
  content negotiation ever matters.
- **RFC 7807 Problem Details envelope.** Bigger architectural
  change; not justified at the current scope.

## Verification

- `make api-gen` succeeds; `schema.d.ts` contains the four new
  schemas under `components.schemas`.
- `make lint` and `make test` pass.
- The new unit test for the `ValidationError` override (§2)
  asserts `loc[-1]` mapping for a deeply-nested malformed body.
- Spot-check via `make dev`:
  - Submit an edit with an invalid year on a machine model →
    frontend renders inline field errors (structured-422 path
    through the `StructuredValidationError` handler).
  - POST a malformed JSON body with a nested-payload error →
    frontend renders the same structured-422 UI; field key matches
    the leaf name. Confirms §2's override and the `loc[-1]`
    decision.
  - Trigger a structured rate-limit 429 (rapid-fire creates against
    a `check_and_record`-protected endpoint) → toast intact via
    `RateLimitErrorSchema`.
  - Trigger a plain 429 (upload that hits media/api.py:76) →
    toast renders the message via the `ErrorDetailSchema` branch.
  - Hit a 404 (unknown slug on a detail-page mutate) → error
    rendering unchanged via `ErrorDetailSchema`.
- Inspect `/api/docs` for one endpoint per file in §3 — confirm
  the 422 / 429 responses appear with the expected schema refs
  (validation vs. detail vs. rate-limit).
- Confirm `parse-api-error.test.ts` passes after the rewrite,
  including the new malformed-body test and the retained
  Pydantic-array fallback test.
