# Detail Refactor Guide

Use this when converting another record type to the section-based detail-page pattern.

## Start Here

1. Define the edit sections first in a shared registry (`*-edit-sections.ts`). Menus, sidebar edit links, accordion `[edit]` links, and the desktop/mobile dispatch all read from it.
2. Convert the route layout to `RecordDetailShell` + `PageActionBar`.
3. Use `resolveDetailSubrouteMode()` — do not hand-roll `isEdit` / `isMedia` / `isSources` booleans.
4. Keep edit-action ownership in the layout. Pages ask for `onEdit`; they don't know whether it opens a modal or navigates.
5. Add the main page sections only after the shell and edit routing are working.

## Required Seams

- **Desktop modal editing + mobile section routes.** The contract this preserves: one open editor at a time (desktop modal enforces it trivially) _and_ real back-button semantics on mobile (section routes give each editor a URL). Collapsing to one mode breaks one of the two invariants.
- **Layout-owned edit action context** (`*EditActionContext.set(editAction)`). Pages consume via `get()`; they never branch on `isMobile`.
- **Per-entity editor-dispatch component** (`*EditorSwitch.svelte`). Owns the `{#if sectionKey === 'x'}` cascade. The layout's `SectionEditorHost` and the mobile `[section]/+page.svelte` both render the switch; the cascade lives in exactly one place. Skipping this means ~90 lines of duplicated dispatch per record type.
- **Typed `initialData` via `Pick<components['schemas']['…']>`**. Define a `*EditView` type for editor props. Catches real field-presence bugs and keeps editors from accepting looser types than they handle.
- **Authenticated-only edit exposure.** The top action bar exposes edit sections _to authenticated users_ — gate on `auth.isAuthenticated` in the layout.

## Page Composition Rules

- **Overview first when a description is present and load-bearing.** When a record's primary content is a grid (multi-model title → Models; manufacturer → Titles), let that lead. Don't show an empty Overview at the top just because the pattern says so.
- **References belongs at the end of the page.** Do not let a reusable overview component bundle its references accordion adjacent to Overview — that silently moves references up past every intermediate section. Use the `createRichTextAccordionState()` + split-component pattern so each page places Overview and References separately.
- **Grids-wider-than-a-screen go below People/Media**, not above.
- **Decide explicitly what stays in the sidebar vs moves into main content vs is duplicated.** On sub-routes the sidebar often moves inline on mobile — pick the behavior per record type.

## Edit Affordances

- Top action bar exposes the full edit-section menu.
- Add sidebar or accordion `[edit]` hooks **only when the block maps 1:1 to a real section**. A sidebar "Companies" block with a `[edit]` link that opens the Basics editor is worse than no link — it teaches the UI to lie.
- Do not invent sections to match a sidebar block's shape.

## Good Extractions

- Detail subroute mode (`resolveDetailSubrouteMode`).
- Mobile edit shell (`EditSectionShell`).
- Layout-breakpoint detection (`createIsMobileFlag(LAYOUT_BREAKPOINT)`). Not "viewport" — it's keyed on the shared layout breakpoint.
- Layout edit-action context (one `*EditActionContext` per record type, Symbol-keyed).
- Per-entity editor-dispatch switch (`*EditorSwitch`).
- Split rich-text overview/references components with a shared state factory (`RichTextOverviewAccordion` + `RichTextReferencesAccordion` + `createRichTextAccordionState`). The factory keeps scroll interconnection intact while letting pages place the two accordions independently.
- Mobile ↔ desktop edit-URL redirect logic (currently ~identical across three record types; extract when a fourth lands).

## Avoid

- Building a generic "detail page framework." Three isomorphic layouts that share named helpers beats one configurable layout that tries to cover every case.
- Hand-rolled `isEdit` / `isMedia` / `isSources` per record.
- Multiple owners for URL sync or modal state.
- **Reading the local state inside the URL→state effect that writes it.** In the `?edit=<segment>` sync pattern, effect 1 (URL→state) should write `editing` unconditionally. An `if (editing !== nextEditing)` guard turns `editing` into a read-dep of effect 1, which re-runs on local writes and reverts the user's click in the same tick. Same-value `$state` writes are already no-ops; the guard is wrong, not an optimization.
- **Defensive rendering of fields an invariant says won't exist.** If single-model titles aren't supposed to have `title.description`, don't render `title_description` on model detail "just in case." Enforce the invariant at write time _and_ strip it from the API schema — otherwise the read side grows permanent dead branches that drift from the rule.
- `:global` in Svelte component styles. Rearchitect; don't escape the scope.
- Stringly-keyed contexts. Use `createContextKey()`-style Symbol keys.

## Test Checklist

- Detail route vs subroute shell behavior.
- Desktop modal edit vs mobile route edit behavior.
- Section order in SSR output.
- Overview `[n]` → References scroll, and References back-link → Overview marker scroll.
- URL ↔ modal state round-trip: menu click updates `?edit=`; reload restores the open modal; back-button closes it.
- Deep-link to a mobile edit route (`/x/slug/edit/name`) from a desktop viewport — no flash of mobile shell before redirect to `?edit=name`.
- Viewport resize across the layout breakpoint while on an edit route — no data loss, no wrong-chrome flash.
- Save flows that change the slug and must navigate to the new canonical route.
- Mixed-edit citation warning per section — verify `showMixedEditWarning` matches what the section actually edits (single-field → `false`; multi-source composite → `true`).
- Dirty-state cancel/navigate prompt fires and respects the user's choice.

## Lessons from Prior Refactors

These are the bugs we actually hit — worth re-reading before the next conversion.

- **Reactivity if-guard in URL sync.** Shipped into manufacturer, propagated to model and title; reverted every menu click on desktop. Fix: drop the guard. See `Avoid` above.
- **References adjacent to Overview.** `RichTextAccordionSections` bundled both accordions. Worked on manufacturer's short page; broke title/model where seven sections separate Overview from where References should sit. Fix: split into two components with a shared state factory.
- **`title_description` dead field.** Backend serialized `title_description` on single-model titles even though the invariant said only the model owns description. Model detail grew a defensive dual-render branch. Fix was twofold: drop from the API schema, and remove the defensive branch.
- **Mixed-edit citation warning miscategorization.** The manufacturer Name section (name + slug) was flagged `true`, then flipped to `false`. Rule of thumb: `true` when the section's fields genuinely come from multiple sources (Basics, External Data); `false` when they share a citation source in practice (Name, Description).
- **Flash of wrong UI on desktop deep-links.** Visiting `/x/slug/edit/name` on desktop briefly rendered the mobile edit shell before redirecting. Fix: gate the shell on `{#if isMobile === true}` and have `createIsMobileFlag` return the browser's synchronous `matchMedia` value on first paint.
