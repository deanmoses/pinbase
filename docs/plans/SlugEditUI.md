# SlugEditUI

## Goal

Make the end-user claims edit path fully support slug edits for existing catalog entities, without touching ingest.

This slice is specifically about the human edit workflow:

- expose slug in the edit UI
- submit slug changes as normal claims
- handle validation and save errors cleanly
- redirect to the new canonical URL after a slug change

It does **not** include:

- ingest changes
- redesigning relationship identity away from slugs
- new entity creation flows
- taxonomy-edit feature work beyond whatever shared edit plumbing is needed

## Why This Is Next

The backend now supports slug claims:

- `slug` is claim-discovered
- PATCH claim endpoints can process slug changes
- the resolver materializes slug winners and handles uniqueness conflicts
- catalog models no longer auto-generate fallback slugs

But the end-user edit UI still behaves as if slugs are not editable:

- form state helpers do not carry `slug`
- edit pages do not render a slug input
- save flows PATCH the current route slug and then stay on the same page
- there is no redirect to the new canonical URL after a slug change

So the backend can do the work, but the user-facing edit path cannot actually use it yet.

## Current Gap

The model edit path shows the issue clearly:

- [`model-edit.ts`](frontend/src/routes/models/[slug]/edit/model-edit.ts) does not include `slug` in `ModelFormFields`
- [`+page.svelte`](frontend/src/routes/models/[slug]/edit/+page.svelte) renders no slug field
- save uses the current page slug in the PATCH URL and only `invalidateAll()` after success

That means a successful slug edit would leave the user on a stale route unless the page explicitly navigates to the new slug.

The same general issue likely exists across the other human edit pages:

- models
- titles
- manufacturers
- people
- corporate entities
- series
- franchises

## Recommended Scope

Do this in two sub-slices, in this order.

### Slice 1: Backend contract + one reference UI path

Use one entity type as the reference implementation. `MachineModel` is the best candidate because it already has the richest edit UI and the most test coverage.

Deliverables:

1. Add backend PATCH tests for slug edits on machine models.
2. Add slug to machine-model form state and diffing.
3. Render a slug input in the model edit page.
4. After save, if the returned slug differs from the current route slug, navigate to the new URL.
5. Preserve the current save UX for non-slug edits.

This slice proves the contract end-to-end before copying the pattern to the other edit pages.

### Slice 2: Roll the same pattern across the other existing-entity edit pages

Apply the same slug-edit behavior to:

- titles
- manufacturers
- people
- corporate entities
- series
- franchises

This should reuse shared helpers/components where possible instead of page-by-page bespoke logic.

## Detailed Plan

### 1. Lock down the backend PATCH contract with tests

Before changing the frontend, add tests that define the expected behavior for slug edits.

For each covered entity type, verify:

- authenticated user can PATCH `fields.slug`
- the response payload returns the new slug
- the resolved object now has the new slug
- the old slug route no longer resolves to the entity
- a duplicate slug is rejected cleanly
- edit history / claim creation still works normally

Start with `MachineModel`. Add the other entity types after the frontend pattern is proven.

Why first:

- it prevents the frontend from guessing at behavior
- it makes route-transition semantics explicit
- it catches any slug-specific backend edge cases before UI work begins

### 2. Introduce a shared slug edit pattern in the frontend

The UI work should not start as seven separate custom implementations.

Add a small shared pattern:

- a slug field row/component or shared helper for edit forms
- optional "regenerate from name" action
- common copy/help text explaining what the slug is

Keep it intentionally simple. The user should be able to:

- see the current slug
- edit it directly
- regenerate it from the current name if helpful

Do **not** build a full creation/proposal wizard in this slice.

### 3. Update edit-state helpers to carry `slug`

Each edit helper module currently has a form-state transform and a patch-body builder. `slug` needs to be added to those helpers so slug edits flow through the same diff machinery as other scalar fields.

For the model path, that means updating:

- [`model-edit.ts`](frontend/src/routes/models/[slug]/edit/model-edit.ts)

Equivalent helpers for the other entity pages should be updated the same way.

This should stay in the scalar-field flow, not become a special parallel request.

### 4. Redirect after slug-changing saves

This is the most important UX behavior in the slice.

Current behavior:

- PATCH `/api/.../{current_slug}/claims/`
- receive updated entity
- `invalidateAll()`
- stay on current route

Required behavior:

- PATCH using the current route slug
- inspect the returned entity slug
- if unchanged, keep current behavior
- if changed, navigate to the new canonical route immediately after save

This should happen for:

- detail/edit page tabs
- subsequent save attempts
- browser refresh/bookmark/share behavior

Without this, slug editing is technically possible but operationally broken.

### 5. Keep the first shipped scope narrow

Do **not** combine this slice with:

- new entity creation
- taxonomy edit UX
- relationship-identity redesign
- ingest cleanup

Those are real follow-ups, but they increase complexity without helping the immediate goal of "make the end-user edit path fully work."

## Edge Cases To Handle

### Duplicate slug

The backend should reject it; the frontend should show a normal save error and leave the user on the current route.

### Rename followed by another edit in the same session

After redirect, the page must be operating against the new slug so a second save does not PATCH the stale URL.

### Save response shape

The redirect logic must rely on the returned entity payload, not on optimistic client-side slug state.

### Transitional slug identity

This plan assumes the current transitional rule from [`ValidationFix.md`](docs/plans/ValidationFix.md):

- bootstrap ingest still uses slug-based identity
- broad slug editing is not yet intended as a high-volume workflow

That is acceptable for this slice. The goal here is correctness of the human edit path, not redesigning long-term identity.

## Suggested Implementation Order

1. Add failing machine-model slug PATCH tests.
2. Make them pass on the backend if anything is missing.
3. Add slug to machine-model edit state + UI.
4. Add redirect-on-slug-change behavior.
5. Add frontend tests for the model edit page.
6. Roll the same pattern to the other existing-entity edit pages.
7. Add a small shared slug field helper if duplication starts to appear.

## Acceptance Criteria

This slice is successful when:

- existing-entity edit UIs expose slug as an editable field
- slug edits are submitted through normal claims PATCH requests
- duplicate slugs are rejected cleanly
- successful slug edits redirect the user to the new canonical URL
- a second save after rename uses the new slug path
- the implementation does not touch ingest

## Follow-ups

Out of scope for this slice, but likely next:

- entity creation UX with explicit slug proposal/approval
- taxonomy edit UIs
- eventual redesign of relationship identity away from slugs before broad live slug editing becomes a routine workflow
