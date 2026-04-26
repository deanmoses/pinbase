# Re-export Barrel

## Context

The frontend currently consumes generated types via indexed access:
`components['schemas']['FooSchema']`, repeated across 88 files. The
pattern is uniform but verbose, exposes the OpenAPI structure at
every call site, and would make the upcoming rename in
[ApiNamingRationalization.md](ApiNamingRationalization.md) more
expensive than it needs to be — every consumer would otherwise
require an indexed-access rewrite per rename commit.

This task introduces a flat re-export barrel at
`frontend/src/lib/api/types.ts` and migrates all 88 consumers to
named imports before the rename starts. The rename then becomes a
small identifier swap (`OldName` → `NewName`) per commit, and an
ESLint guardrail keeps the old pattern from creeping back.

## Approach

Generate the barrel rather than hand-maintain it. A small script
wired into `make api-gen` enumerates the keys of
`components['schemas']` and emits `types.ts` parallel to
`schema.d.ts`. Both are gitignored, so the barrel can never drift
from the generated types.

The barrel is flat. Grouping by app would need metadata the OpenAPI
doc doesn't carry; grouping by read/write is lossy.

The one-time consumer sweep converts every
`components['schemas']['XSchema']` indexed-access reference to a
named import from `$lib/api/types`. At this point the names still
carry the `Schema` / `In` / `Out` suffixes — the barrel is exposing
whatever exists today. That's fine; the rename in
[ApiNamingRationalization.md](ApiNamingRationalization.md) cleans
up the names and the barrel regenerates automatically.

Pair the sweep with an ESLint `no-restricted-syntax` rule banning
`components['schemas']` outside `client.ts` and `types.ts` so the
old pattern can't quietly come back during the rename or after.

No collisions: verified during _Document rationalized API names_
(see [ApiNamingRationalization.md](ApiNamingRationalization.md)).
