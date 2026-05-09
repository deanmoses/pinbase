# Centralized Test Factories

## Scope

This PR introduces `make_user()` as the first instance of a project-wide convention: **one `test_factories.py` per app**, exporting `make_<model>(**overrides)` helpers for the models that app owns. The only existing example is [apps/provenance/test_factories.py](../../../backend/apps/provenance/test_factories.py), which covers `ChangeSet` — and only because DB check constraints make raw `ChangeSet.objects.create(...)` easy to get wrong. Every other model in the project (`Title`, `Manufacturer`, `CitationSource`, etc.) is constructed inline in tests with no central source of truth for "what does a default one look like."

`User` is just the first model where the duplication is about to become actively painful (see Authz Step 4 below). The same latent debt sits on every other heavily-tested model; they just haven't had a forcing function yet.

## Problem

The test suite has no shared helper for creating `User` objects. There are 42 local `user` fixtures and ~108 inline `User.objects.create_user(...)` calls in test bodies. Every one of the 42 fixtures is byte-identical:

```python
@pytest.fixture
def user(db):
    return User.objects.create_user(email="editor@example.com")
```

That uniformity is itself the smell — it means every test wants the same thing (an editor), and there is no shared definition of what an editor is. Today the duplication is invisible because the lines agree. Tomorrow they need to disagree (some tests want a verified user, others an unverified one; some need two distinct users in one test), and the cost of the disagreement is paid 42× plus 108×.

Two forcing functions are imminent, both from [Authz.md](Authz.md):

- **Step 4 (verification gate)** — a new `email_verified` boolean column on `User`, defaulting to `False`. Once `email_verified` is wired into every launch activity's rule, every test that exercises a gated write endpoint with a default-constructed user starts hitting a 403.
- **`claim.revert` target-aware rule** — "you can revert your own claim but not someone else's" needs two _distinct_ users in a single test. Hardcoding `email="editor@example.com"` everywhere makes that awkward.

Later activity-layer rules (account age, reputation, ban state, rate limits) will each hit the same wall.

Without a central helper, the options are:

- Update all 42 local fixtures plus 108 inline call sites to pass `email_verified=True` (large diff, mostly noise).
- Default `email_verified=True` in `UserManager.create_user` (production code shaped by test convenience).
- Live with broad test breakage and fix tests reactively.

A shared helper makes this a one-line addition to the test layer instead of a sprawl, and amortizes against the next `User` field addition.

## Suggestion

Two pieces, deliberately complementary:

1. **A project-root `conftest.py` `user` fixture** that returns `make_user()`. Pytest fixture shadowing means every existing local `def user(db): ...` keeps working unchanged today. When Step 4 lands, the 42 local fixtures can be deleted in a near-mechanical sweep — tests then inherit the project-default `user`, which by then defaults to `email_verified=True`. Flipping the default touches one file, not 30+.

2. **`apps/accounts/test_factories.py` exporting `make_user(**overrides)`**, mirroring the existing [apps/provenance/test_factories.py](../../../backend/apps/provenance/test_factories.py) shape. This is what new tests reach for when they need overrides, two distinct users in one test (`claim.revert`target-aware tests), or a non-default state. The conftest fixture is a thin`return make_user()` so there is one source of truth for what a default user looks like.

These are not alternatives — they cover different call shapes:

- Tests that want "give me an editor": `def test_x(user): ...` — uses the conftest fixture.
- Tests that want overrides or multiple users: `make_user(email_verified=False)`, `author = make_user(); reverter = make_user()` — uses the function.

This PR introduces both **and does the fixture sweep up front**: 40 of the 42 byte-identical local `user` fixtures are deleted (the project-root fixture takes over via shadowing). The exceptions:

- **One fixture retained** ([apps/provenance/tests/test_rate_limits.py](../../../backend/apps/provenance/tests/test_rate_limits.py)) because it has a teardown call (`reset_for_user`) that the project-root fixture doesn't provide.
- **Three brittle literal-username assertions migrated to dynamic form** (`assert data["user_display"] == user.username` instead of `== "editor"`). The literal strings only worked because the username derivation happened to produce them from `editor@example.com`; switching to dynamic lookup let those files use the project-root fixture too.

The ~108 inline `User.objects.create_user(...)` calls in test bodies are **not** migrated in this PR — those mostly exist because the test needs a specific email or multiple users, so they're a per-call-site judgment, not a mechanical sweep. Step 4 (the verification gate) only needs to touch inline call sites that actually start 403'ing under `email_verified=True`, plus flip the default in `make_user`. The 40-fixture sweep means the _fixture_ path of Step 4 is already done.

New tests use `def test_x(user): ...` (project-root fixture) for the simple case, or `make_user(...)` directly when they need overrides or multiple users.

## Next candidates

Once the convention is established with `make_user()`, the models with the most inline `Model.objects.create(...)` calls are the obvious next targets. Counts of inline `<Model>.objects.create` across `apps/`:

| Model             | Inline creates | App      | Notes                                                                                      |
| ----------------- | -------------- | -------- | ------------------------------------------------------------------------------------------ |
| `Title`           | 131            | catalog  | Top of the catalog hierarchy; appears in nearly every catalog test.                        |
| `Manufacturer`    | 118            | catalog  | Almost always created alongside `Title` / `Model`.                                         |
| `CitationSource`  | 106            | citation | Required setup for any test that touches citations.                                        |
| `Theme`           | 56             | catalog  | Taxonomy fixture; many catalog tests need at least one.                                    |
| `Location`        | 54             | catalog  | Self-referential parent chains make manual construction tedious — factory wins extra here. |
| `Person`          | 47             | catalog  | Credit-role tests need several at once.                                                    |
| `MediaAsset`      | 46             | media    | Has constraints around primary/category that a factory can encode safely.                  |
| `CorporateEntity` | 41             | catalog  | Same shape as Manufacturer/Person.                                                         |
| `System`          | 29             | catalog  | Lower volume but appears across many test files.                                           |
| `Model`           | 24             | catalog  | Lower count because most tests reach for `Title`; will rise as model-level tests grow.     |

These are not commitments — each migrates when the next forcing function (a new field, a new constraint, a target-aware authz rule) arrives. The convention is the contribution; the migration order falls out of need.

The catalog block (`Title`, `Manufacturer`, `Theme`, `Location`, `Person`, `CorporateEntity`, `System`, `Model`) will likely land together when the first one needs it, since they're co-constructed — a `Title` factory that doesn't have a `Manufacturer` factory to delegate to is half-built. Per [AppBoundaries.md](../../AppBoundaries.md) those all live in `apps/catalog/test_factories.py`.

## Out of scope for this doc

The session that picks this up should do its own analysis on:

- The email-uniqueness strategy (UUID suffix, sequence counter, `pytest-randomly`-friendly hash). Hardcoding will break the moment a test wants two users.
- What other defaults (`is_staff`, `password`, `is_active`) the helper should set explicitly versus leave to the manager.
- Whether to also delete the 42 local fixtures opportunistically in this PR (cheap if the conftest fixture lands first; can be a follow-up).
- Whether the inline `User.objects.create_user(...)` call sites should be migrated mechanically or left for Step 4 to touch only as needed.
