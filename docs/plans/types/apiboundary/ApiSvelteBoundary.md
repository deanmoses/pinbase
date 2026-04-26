# API Boundary Improvements

## Context

This doc contains a set of improvements that make the Django Ninja + SvelteKit boundary boundary more ergonomic for humans and AIs to read, more correct on
the failure path, and more resistant to drift.

The original concern that started this — `frontend/src/lib/api/schema.d.ts`
is 10,330 lines and hard for AIs to reason about — turned out to be
mostly a symptom of weak ergonomics around how the generated types are
consumed (88 files re-aliasing `components['schemas']['XSchema']`),
not a problem with the file itself. About 23% of the file is
`?: never;` boilerplate from `openapi-typescript`'s output style and
isn't worth fighting.

## Direction

Stand up the re-export barrel and ESLint guardrail so later sweeps stay small.
Close the real correctness gap (typed error responses). Rename
schemas at the source so backend, OpenAPI, and frontend share one
vocabulary. Pin the resulting conventions with tests.

## Tasks

### Document rationalized API names

Convention rules and full per-app rename tables in
[ApiNamingRationalization.md](ApiNamingRationalization.md). Pure
paper work — no code changes. Output is the finalized rename table
that _Rename API schemas on the backend_ executes against.

### Re-export barrel

Tracked in [ApiBarrel.md](ApiBarrel.md). Generate a flat re-export
barrel at `$lib/api/types.ts` and sweep the 88 indexed-access
consumers to named imports before the rename starts, so each rename
commit's frontend changes are small identifier swaps rather than
indexed-access rewrites. Pair with an ESLint guardrail banning
`components['schemas']` outside `client.ts` and `types.ts`.

### Type error responses

The largest real gap in the boundary. Today only delete endpoints
declare typed 4xx response schemas; ~80% of mutating endpoints
declare 200 only, and validation errors flow through a global
exception handler at `backend/config/api.py:89-93` that the OpenAPI
contract never sees. The frontend's `parseApiError` consequently
handles three different observed runtime shapes — a sign the
contract isn't pinned.

The unit of work is: define a canonical error response schema (or
schemas — one for validation, one for generic), declare it on every
mutating endpoint's `response={...}`, regenerate types, and simplify
`parseApiError` to match the now-typed surface. Frontend gains real
types on the failure path; parsing can stop guessing.

Any new error schemas added here land under the old naming
convention and get caught up in the
_Rename API schemas on the backend_ pass — no extra round trip.

Open questions the session should resolve:

- Whether one schema covers both validation and generic errors, or
  whether they're distinct (and if distinct, how the union is
  declared so the frontend can discriminate).
- Whether the existing `ErrorDetailSchema` in `apps/core/schemas.py`
  is the right home or whether a new shape is needed.
- How the global exception handler's output is brought into the
  contract — declared as a default response, attached to specific
  status codes, or something else.
- Scope of "mutating endpoints" — POST/PATCH/DELETE only, or also
  GETs that can return 404/403.

This is the task most likely to surface backend changes that
reshape later tasks; expect to fold learnings back into
_Boundary tests_ before starting it.

### Rename API schemas on the backend

Tracked in [ApiNamingRationalization.md](ApiNamingRationalization.md).

Execute the rename table from _Document rationalized API names_:
rename Ninja schema class names on the backend, at the source.
Drop the `Schema` suffix, fix the `In`/`Out` divergence in the
media app, scope generic names (`Variant`, `Source`, `Stats`,
`Recognition`, `Create`), kill ghost types (`Input`, `JsonBody`).
The contract itself uses the desired names end-to-end — the
OpenAPI doc, the generated `schema.d.ts`, and every frontend
consumer all share one vocabulary.

Any error schemas introduced by _Type error responses_ are
renamed in this same pass.

Each per-app commit renames backend classes, regenerates the
barrel automatically (via `make api-gen`), and does a small
codemod on consumer named imports (`OldName` → `NewName`). Smaller
diffs than rewriting indexed-access references, and the ESLint
guardrail from _Re-export barrel_ keeps the migration honest.

This inverts _Boundary tests_ convention-enforcement rules (from
"names end in `Schema`" to "names do not end in `Schema`").

See the rationalization plan for the convention rules, the full
per-app rename tables, and the per-app commit sequence.

### Boundary tests

After the previous tasks land, the conventions worth pinning will be clearer.
Likely candidates, to be confirmed against what the prior tasks
actually established:

- Schema suffix discipline: per
  [ApiNamingRationalization.md](ApiNamingRationalization.md), no
  schema name ends in `Schema`, `In`, or `Out`; outputs are bare or
  use a role suffix (`…Detail`, `…ListItem`, `…GridItem`, `…List`,
  `…Ref`); inputs use `…Input`, `…Patch`, or `…Create`. The test
  asserts the negative (no `Schema`/`In`/`Out` suffixes in
  `components.schemas`) plus a positive check that every name
  matches one of the allowed role patterns.
- Schemas live in `schemas.py`, not embedded in endpoint files
  (`apps/citation/api.py` has 15 inline classes; `apps/accounts/api.py`
  has 4).
- Every mutating endpoint declares typed 4xx responses (the rule
  _Type error responses_ will have established).
- Operation IDs are explicit, not inferred from function names —
  so backend renames don't silently change the OpenAPI contract.
- Every named schema in `components.schemas` is re-exported from
  `$lib/api/types.ts` (the rule _Re-export barrel_ will have
  established).

Existing precedent at `backend/apps/catalog/tests/test_api_schema_boundaries.py`
is the model: assertions against the live OpenAPI doc and module
locations, not text-pattern checks.

The session for this task should treat the candidate list as input,
not as a spec — some items may turn out to be too noisy to enforce,
others may have been resolved in earlier tasks in ways that change
what the test should assert.

## Verification

Each task verifies on its own terms — `make lint`, `make test`,
`make api-gen`, and a spot-check of the running app via `make dev`
where appropriate. There is no end-to-end verification step for
the plan as a whole; if each task lands clean, the boundary is
materially better than it was.

## Follow-ups

See [ApiSvelteBoundaryFollowups.md](ApiSvelteBoundaryFollowups.md).
