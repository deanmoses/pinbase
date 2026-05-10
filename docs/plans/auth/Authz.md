# Editorial Activity Authorization

## Problem

We need to be able to put checks around editor and moderator activity without wiring every call site to one specific check.

Email verification -- [Verification.md](Verification.md) -- is the first concrete case: catalog edits should require a verified email so disposable email-password accounts cannot immediately write claims. But the authorization decision should not be named or modeled as "email verification" at every Svelte editor, API endpoint, or claims write helper. That would make the next constraint -- moderator role, account age, rate limit state, reputation, abuse flag, scoped delete permission, etc. -- require another audit of every edit path.

The product rule we care about is not "has verified email." It is "may perform this activity." Email verification is only one input into that decision.

## Proposal

Introduce a small policy/capability layer for user activities. Call sites ask whether a user may perform a named activity, and the centralized policy decides which checks currently apply.

Examples of activity names:

- `catalog.edit`
- `catalog.create`
- `catalog.delete`
- `claim.revert`

Backend write paths should depend on activity authorization, not directly on `email_verified`. For example, a catalog claim write should require `catalog.edit`; the policy for `catalog.edit` can initially require authentication, an active account, and verified email. Later, the same policy can add account-age, role, reputation, moderation, or rate-limit constraints without changing every catalog editor.

The frontend should follow the same language but must not reimplement the policy. The backend exposes capabilities through two surfaces, used together: a `/me/capabilities` endpoint for target-less activities (`catalog.create`), and per-resource capability hints embedded in resource responses for target-aware activities (`claim.revert` on a specific claim, `catalog.delete` on a specific entity). Both compute their answers via `policy.check`; neither is the sole source. Structured denial responses return stable blocker codes from a closed registry -- `verification_required`, `moderator_required`, etc. -- mapped to user-facing copy in one place, so shared UI can explain the problem without each editor knowing the underlying authorization rules.

This is the standard policy-based / capability-based authorization shape: call sites request an action, central policy evaluates roles and attributes. For Flipcommons, a lightweight in-repo policy module is enough; adopting a full external authorization engine would be premature.

## Principles

- **Object-level-ready signature from day one.** The policy signature is `check(user, activity, target=None, context=None)`. Launch rules don't use `target` or `context`, but having the parameters present means later rules that need them (e.g. "you can revert your own claim but not someone else's", or "respect the rate-limit state middleware just computed") can be added without touching call sites.
- **Default-deny, single registry.** The registry of activities lives in one importable module, so the route-inventory test, the capabilities endpoint, and humans reading the codebase all see the same authoritative set. A missing rule is a programming error, not a permission grant: `check()` raises `LookupError` rather than returning `Deny`, so misconfiguration surfaces as a 500 with diagnostic context rather than a misleading 403. The registry-completeness test (`test_authz_registry_complete`) keeps that branch dead at runtime.
- **Pure decisions; no I/O in the policy.** `check` is a pure function over its inputs. The policy reads attributes on already-loaded objects; it does not query the DB, hit the cache, or call out to other services. New data dependencies are assembled by the caller (or by middleware that builds `context`) before the call. This keeps decisions cheap, testable without fixtures, and replayable from logs. Enforced statically by per-rule target Protocols and dynamically by a dev/test recording proxy — see [Enforcing pure decisions](#enforcing-pure-decisions). Corollary: serializers that embed capability hints must prefetch the attributes the policy reads, so the embed loop doesn't lazy-load behind the policy's back.
- **Decisions are structured, not boolean.** `check` returns either `Allow` or `Deny(code, context)` from the closed denial-code registry — never a bare bool. Throwing away the denial code at the boundary throws away the half of the answer that drives UX.
- **Anonymous users go through the policy.** The policy is invoked for unauthenticated requests too; they deny with `auth_required`. This means `/me/capabilities` works for logged-out callers (returning everything false) and the SPA doesn't branch on "logged in" before asking what's allowed. HTTP 401 stays reserved for "your session is invalid," not "you're signed out."
- **Mutations always go through the policy; reads are public by default.** Catalog reads, lookups, and search don't run through `policy.check` — there is no `catalog.read` activity. Authenticated-only reads (`/me`, drafts, notifications) gate on `is_authenticated`, not the policy. The exception: a small, deliberate set of sensitive reads (e.g. moderation tooling, ban audit trails, abuse-report inboxes) may be named as activities and gated, but only when the read is genuinely privileged. The default for new read endpoints is "no activity gate."
- **Backend is the source of truth; the frontend reflects.** Never mirror policy logic in JS. Two engines will drift.
- **Activities are product-meaningful, not data-model-shaped.** Resist granularity like `catalog.edit.title.scalar` -- that leaks the schema into the policy namespace and dissolves the abstraction.
- **Activities are named for what's being gated, not who can do it.** Don't name an activity after the role currently allowed (`moderation.action`, `admin.thing`) — roles change, the gated thing doesn't. The "thing" is usually an act the call site is performing (`entity.merge`, `claim.override`, `account.ban`), but it can also be a tooling surface (`django_admin.access`) or a user-state predicate (`rate_limit.exempt`); both are legitimate as long as the name describes what's gated, not the role permitted. Let the policy decide who qualifies. Add an activity when its call site is being built, not in advance.
- **Don't use Django's permission framework.** This activity layer is parallel to Django perms, not built on top. Per-model perms compose poorly with attribute checks (verified email, account age, rate limit), and we'd end up wrapping them anyway.
- **Denial codes are a closed enum.** One registry, mapped to user-facing copy. No ad-hoc strings spelled differently across editors.
- **Rate-limiting is policy-aware, not policy-owned.** Enforce early in the request path -- as early as the limit's scope allows (per-IP/per-user floods in middleware; activity- or target-scoped limits where the target is known). The policy may reflect rate-limit state for UX but is not the sole gate.

## Anti-goal: NO PERMISSION CHANGES other than email-verified

For the initial roll-out, the ONLY permission change we are making is requiring every CRUD operation to be email-verified. Do NOT change which users can do what, except for email-verified.

## Initial activities

The launch set. Each row is what the policy enforces today; later constraints (account age, reputation, rate limits, moderation flags) layer in without changing call sites.

| Activity         | Rules at launch                                  | Notes                                                                                                           |
| ---------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `catalog.edit`   | authenticated, active, email-verified            | Writes on existing entities.                                                                                    |
| `catalog.create` | authenticated, active, email-verified            | Separated from edit so creation can tighten independently later (e.g. account age) without touching edit paths. |
| `catalog.delete` | authenticated, active, email-verified            | Separated from edit so deletion can tighten independently later without touching edit paths.                    |
| `claim.revert`   | authenticated, active, email-verified            | Separated from edit so revert can tighten independently later without touching edit paths.                      |
| `changeset.undo` | authenticated, active, email-verified            | Inverts a delete-changeset (post-delete Undo toast). Target-aware: today scoped to the changeset author.        |
| `citation.edit`  | authenticated, active, email-verified            | Citation-source CRUD plus citation-instance writes attached to claims.                                          |
| `media.edit`     | authenticated, active, email-verified            | Upload, detach, set-primary, set-category — all media-attachment claim writes.                                  |
| `kiosk.edit`     | authenticated, active, email-verified, superuser | Kiosk config CRUD.                                                                                              |

- "Active" means `is_active=True` — the account is not currently deactivated for any reason (self-deactivation, dormant cleanup, etc.). Banning, when it ships, will be a separate predicate with a separate denial code so the SPA can render different copy.
- "Authenticated" means a logged-in session, not anonymous.

The four activities below the divider were added per "Add an activity when its call site is being built, not in advance" during the phase-1 inventory pass — same launch rules as the original four, separated only so each can tighten independently later.

## Decision shape

The policy entry point and its return type:

```python
def check(
    user: PolicyUser,              # Protocol covering both authenticated User and AnonymousUser
    activity: Activity,            # closed enum of registered activity names
    target: Model | None = None,   # a record of the domain object the activity acts on, when applicable
    context: PolicyContext | None = None,  # caller-assembled ambient state (rate-limit, etc.)
) -> Decision: ...


@dataclass(frozen=True)
class Allow: ...

@dataclass(frozen=True)
class Deny:
    code: DenialCode             # closed enum
    context: Mapping[str, Any]   # shape declared per code

Decision = Allow | Deny
```

`Allow` and `Deny` are returned by the policy and serialized at the API boundary; the same shapes flow through both surfaces.

Individual predicates also return `Decision`, not `bool`. Each predicate names its own failure code (`is_authenticated` denies with `auth_required`, `is_active` with `account_deactivated`), which is what makes the [denial-code priority](#denial-code-priority) rule work — when multiple predicates fail, the evaluator picks the highest-priority `Deny`. A `bool`-returning predicate would discard the code and force the evaluator to reverse-engineer it, which can't be done correctly when the same predicate could plausibly fail for different reasons.

## Module layout

Per [AppBoundaries.md](../../AppBoundaries.md), the engine lives in `core` and per-app rule files register into a single central registry.

```text
backend/apps/core/authz/
  types.py        # Activity StrEnum, Decision, Allow, Deny, DenialCode enum, PolicyUser Protocol
  registry.py     # the activity registry + register() entry point
  predicates.py   # is_authenticated, is_active, email_verified, base Predicate
  evaluator.py    # check(user, activity, target, context) — the entry point
```

Per-app rule files declare each app's activities and rules:

```text
backend/apps/catalog/authz.py     # catalog.edit, catalog.create, catalog.delete
backend/apps/provenance/authz.py  # claim.revert
backend/apps/media/authz.py       # media.* activities
# etc.
```

Each app's `apps.py: ready()` imports its `authz` module so registration happens at startup. The route-inventory test then walks the populated registry and asserts every mutating route is mapped to a registered activity.

### Reading markers off views

The marker decorators (`@requires`, `@gated_inline`, `@public_mutation`) stamp string-keyed attributes (`_authz_activity`, etc.) on the view callable. Consumers must read those markers via the typed accessors in `core/authz/markers.py` rather than poking at the attributes directly:

```python
from apps.core.authz.markers import (
    get_required_activity,        # @requires      → Activity | None
    get_gated_inline_activity,    # @gated_inline  → Activity | None
    get_public_reason,            # @public_mutation → str | None
)
```

Each accessor wraps the `getattr(...)` lookup with an `isinstance` narrow, so the return type is genuinely correct (a hand-stamped `_authz_activity = "catalog.edit"` string returns `None` instead of silently impersonating an `Activity`). Future surfaces — `/me/capabilities` (Phase 7), embedded-hint serializers, capability pre-loaders — must use these accessors. The string constants `ACTIVITY_ATTR` / `GATED_INLINE_ATTR` / `PUBLIC_ATTR` are still exported for the route-inventory test, which legitimately enumerates marker names to detect double-stamping; nothing else should need them.

### Why `core`, not `accounts`

`core` is the right home because the engine is project-wide infrastructure with no dependencies, and every middle- and top-tier app calls into it. Putting it in `accounts` would invert the dependency direction — `accounts` is a peer of `core`, not a foundation under the rest of the project, and nothing currently imports from `accounts` (apps use `AUTH_USER_MODEL` strings for FKs). Authz isn't account-specific behavior; it's a gate that _reads_ user attributes.

The User-typing concern is handled by a small `PolicyUser` Protocol in `core/authz/types.py` declaring just the attributes the engine reads (`is_authenticated`, `is_active`, `email_verified`). The engine doesn't import the concrete `User` class.

### Why per-app rule files

Target-aware rules need to type-hint and read attributes from their app's models (a `Claim`, a `Title`, a `MediaAsset`). If those rules lived in `core`, `core` would have to import from every app above it, which the boundary rules forbid. Putting rules next to the models they care about — and registering them into a central registry — keeps `core` clean while the registry stays the single source of truth.

## Enforcing pure decisions

The "no I/O in the policy" principle is enforced primarily by per-rule target Protocols + mypy: the predicate's parameter is typed as a narrow Protocol, so reading any attribute outside that Protocol is a static type error caught at definition time. Tests that need to verify a target-aware predicate doesn't trigger a query wrap the call in Django's `CaptureQueriesContext` and assert the count is zero. No bespoke runtime infrastructure.

### Per-rule target Protocols

The engine's `target` parameter is generic (`Model | None`); each per-rule predicate declares its own narrower Protocol covering exactly the attributes that rule may read. The Protocol lives next to the predicate, in the consuming app:

```python
# apps/provenance/authz.py
from typing import Protocol

class ClaimPolicyView(Protocol):
    """The Claim attributes this app's policy is allowed to read."""
    @property
    def id(self) -> int: ...
    @property
    def author_id(self) -> int: ...
    @property
    def is_locked(self) -> bool: ...

def is_claim_author(user: PolicyUser, claim: ClaimPolicyView, context) -> Decision:
    if claim.author_id != user.id:
        return Deny(DenialCode.ROLE_REQUIRED)
    return Allow()

def claim_not_locked(user: PolicyUser, claim: ClaimPolicyView, context) -> Decision:
    if claim.is_locked:
        return Deny(DenialCode.ROLE_REQUIRED)
    return Allow()
```

Attributes are declared as `@property`, not variable annotations. Variable annotations in a Protocol are settable and invariant, which means a class exposing the attribute as a read-only property — or as a `Literal` class constant, like `AnonymousUser.is_active = False` — fails the structural match. `@property` makes the surface read-only and covariant, which is what we actually want: the policy reads, never writes, and a `Literal[False]` must be acceptable where `bool` is declared. The same convention applies to `PolicyUser` in `core/authz/types.py`.

Protocols are structural — `Claim` instances satisfy `ClaimPolicyView` automatically by having the right attributes — so the engine still passes real model instances at runtime; nothing about the call changes. The change is at the _predicate_ boundary: inside the predicate, the type checker sees only the Protocol's attributes. Writing `claim.author.is_moderator` is a static type error because `ClaimPolicyView` declares `author_id: int`, not `author: User`.

This makes "I want to traverse a relation" a visible policy decision: extending the Protocol is something a reviewer notices, and the diff shows the new attribute being added to the read surface. The Protocol also doubles as the contract for what serializers must `select_related` / `only(...)` when embedding capability hints — grep `ClaimPolicyView` to find the exact prefetch list.

The same pattern is used for `PolicyUser`: the engine declares the shared user surface (`is_authenticated`, `is_active`, `email_verified`); per-rule Protocols declare per-target surfaces.

### Verifying purity in tests

Static checking covers the typical mistake: reading an attribute outside the Protocol. It doesn't cover dynamic access (`getattr(claim, "author")` bypasses the type system) or a Protocol that declares a relation but the caller forgot to prefetch (the type checker is happy; runtime still N+1s).

**Every target-aware predicate must have at least one test that wraps the call in `CaptureQueriesContext` and asserts zero queries.** This is a hard rule, not a recommendation — without bespoke proxy infrastructure, this assertion is the only thing standing between "convention says predicates are pure" and "production N+1 inside a serializer loop."

```python
from django.db import connection
from django.test.utils import CaptureQueriesContext

def test_is_claim_author_is_pure(claim):
    with CaptureQueriesContext(connection) as ctx:
        decision = is_claim_author(user, claim, None)
    assert len(ctx) == 0, f"predicate ran {len(ctx)} queries"
    assert isinstance(decision, Allow)
```

`CaptureQueriesContext` is Django's canonical query-counting helper. The assertion documents the test's intent — "this predicate must be pure" — at the call site, rather than relying on a fixture that's easy to forget.

The `assert_predicate_is_pure(predicate, user, target=None, context=None)` helper lands with the **first target-aware predicate** (expected with the Phase 8 per-target rules — `is_claim_author` / `claim_not_locked`), not with Phase 4. Phase 4's only new predicate is `email_verified`, which is target-less; a target-less predicate's purity is already covered by the `is_authenticated` / `is_active` purity tests. Pre-extracting the helper in Phase 4 would design it for one shape (target-less), then need re-shaping when target-aware predicates arrive — better to defer.

## Denial responses

HTTP wire format on denial — nested under `detail` to match the project's structured-error idiom (see `ValidationErrorSchema` / `RateLimitErrorSchema` in `apps/core/schemas.py`):

```json
HTTP 403
{
  "detail": {
    "kind": "policy_denied",
    "message": "Verify your email to start editing.",
    "code": "verification_required",
    "context": { "email": "alice@example.com" }
  }
}
```

`message` is an English fallback so the API is usable without the SPA. The SPA ignores it and renders its own copy from `code` via a single mapper module — one place per code maps to `{ title, body, primaryAction }`. Each code's `context` shape is part of the registry and part of the API contract; adding or removing a key is a breaking change.

The Phase-6 denial-code mapper layers _on top of_ the existing base-message extraction in `frontend/src/lib/api/parse-api-error.ts`, not in place of it. The parser already special-cases `validation_error` (it has field-level errors) and falls through to `plain(detail.message)` for every other structured error via the `StructuredErrorBodySchema` base contract. Phase 5 adds a separate `code → { title, body, primaryAction }` mapping that the SPA's render layer consults; the parser's job stays "extract a message string." A new structured error variant on the backend that's content with the base `message` requires zero changes to the parser — only the render mapper, and only when the code wants custom copy.

All structured-detail flavors carry `kind` — `validation_error`, `rate_limit`, `policy_denied` — and the frontend extractor dispatches by `detail.kind`. New variants subclass `StructuredApiError` (declaring `kind` and `status` as class attributes plus a `to_body()` method) and declare a matching `kind` literal on their body schema; a single shared exception handler in `config/api.py` wraps the response.

Routes are not currently required to declare `403: PolicyDeniedSchema` specifically in their `response=` map. The global exception handler in `config/api.py` produces the structured body regardless, and `parse-api-error.ts` dispatches on `detail.kind` at runtime — so generic per-code copy (the Phase 5 mapper) works without typed knowledge of which operations can deny. The frontend's denial mapper keys off `error.detail.code`.

There is a related but orthogonal contract: `test_post_patch_delete_declare_4xx_responses` requires every mutating endpoint to declare _some_ 4xx response (token presence, not comprehensive enumeration). For routes with input validation or missing-object lookups, 422 / 404 declarations satisfy that test, and policy 403 is left undeclared. For routes whose only error mode is the policy gate (today, just `create_config` in `apps/kiosk/api/configs.py`), the policy 403 is the natural — and currently the only — 4xx to declare; the union `PolicyDeniedSchema | ErrorDetailSchema` is used so a future inline `HttpError(403, "...")` would still type-check. Both shapes are fine; the 4xx-presence test does not care _which_ 4xx is declared, only that one is.

**Revisit after Phase 8.** Declaring `403` per route would buy a typed `error.detail.code` on the generated SvelteKit client, which only matters if the SPA grows _per-(route, code)_ special-casing — different copy or remediation for the same denial code depending on which operation produced it. Today the SPA has none of that, and the Phase 5 mapper deliberately keeps copy generic. Phase 8's embedded capability hints further reduce catch-and-react sites by letting the SPA disable affordances pre-emptively. After Phase 8, audit the SPA for per-(route, code) handling: if it has emerged, sweep all `@requires` routes to declare `403: PolicyDeniedSchema` (or the union `PolicyDeniedSchema | ErrorDetailSchema` where an inline `HttpError(403, "...")` also fires) and add a route-inventory-style test that walks `@requires` markers and asserts each operation's response map declares 403. Otherwise, leave the contract as-is. Watch Phase 5 for an early signal — if writing the denial-code mapper drives a reach for route-aware overrides, pull the decision forward.

### Denial code priority

Multiple predicates can fail simultaneously (unverified email and deactivated account). The policy returns one code, not a list. The priority order is sorted by **actionability** — the code that tells the user the most useful thing first wins:

1. `auth_required` — user is anonymous
2. `account_deactivated` — `is_active` is false (self-deactivated, dormant cleanup, etc.)
3. `account_banned` — explicit ban (added when banning ships; separate from `account_deactivated` so the SPA can render different copy)
4. `role_required` — moderator/admin needed
5. `verification_required` — email not verified
6. `rate_limited` — soft, retry possible

Telling a deactivated user to verify their email is the wrong UX; the priority order is what prevents that. The same logic puts `role_required` above `verification_required`: an unverified non-moderator who tries a moderator-only action should hear "moderator only," not "verify your email" — verifying won't grant them the access they're after, so the role message is the more useful one. The order is global to the registry, not per-activity.

### Audit logging

Denials are logged at `info` with `(user_id, activity, code, target_id)`. Allows are logged at `debug` (mostly off in prod). Logging is the _caller's_ job — the policy returns a `Decision` and the calling middleware/decorator emits the log. Keeps the policy pure.

Tests that verify logging assert against a typed `CapturedAuthzLog` dataclass + pytest fixture in `apps/core/tests/test_authz_enforcement.py` — a small handler-based capture that pulls `extra=` keys off `LogRecord` into a typed shape. Future per-activity audit-log assertions should reuse the existing `authz_logs` fixture rather than reaching into `caplog.records[0].__dict__["activity"]` (which works at runtime but is `Any`-typed, so mypy can't catch a renamed `extra` key). The fixture documents the contract — every authz log record carries `(message, level, user_id, activity, code)` — and a missing key fails at fixture-translation time, not silently in a test that happens not to read it.

## Integration surface

The route-inventory test only works if there is one canonical way to gate a route. Static walking can see route signatures, dependencies, and decorators; it cannot see the body of a view function. If half the call sites use a Ninja dependency and half call `check()` inline, the inventory test is silently incomplete — which is the worst failure mode for a test whose job is catching missing gates.

### Canonical form: `@requires` decorator

Django Ninja does not have FastAPI-style dependency injection (`deps=` / `Depends`). The canonical gating form for this codebase is a Python decorator stacked directly under the route registration, the same shape Django's `@login_required` uses:

```python
# apps/catalog/api.py
@router.patch("/entities/{id}", auth=session_auth)
@requires(Activity.CATALOG_EDIT)
def patch_entity(request, id: int, ...): ...
```

`@requires(activity)` lives once in `core/authz/` and is **staged across two PRs**. Call sites apply the decorator the same way in both phases — only the decorator's body changes:

1. **Inventory phase**: `@requires` is a marker-only no-op. It stamps `_authz_activity = Activity.CATALOG_EDIT` on the wrapped view function so the inventory walker can see it without reading the body. No call into a policy module — the engine doesn't exist yet.
2. **Enforcement phase** (a later PR): `@requires`'s body is updated to also run `policy.check(request.user, activity, target=None)` and raise a structured 403 on deny. The marker stays. No call site changes.

This is what lets the inventory ship before the engine exists: applying the decorator everywhere is safe even when its body is a no-op, because the only side effect is the attribute stamp. See [Implementation phases](#implementation-phases) for the full PR sequence.

The decorator order matters: `@requires` must be _inside_ `@router.patch` so Ninja registers the wrapped callable. Reverse the stack and the marker sits on the Ninja-wrapped operation, not on the function the walker reaches via `Operation.view_func`.

### Constraints on wrapping decorators

Any decorator that wraps a Ninja-registered view — `@requires` today, plus any future variant (target-aware, async, dry-run, capability-hint pre-loader) — must rebuild the wrapper so it carries the _wrapped function's_ `__globals__`, not the decorator module's. A vanilla `@functools.wraps` wrapper will work for hand-written views and silently break factory-built ones.

Ninja resolves forward-ref annotations via `getattr(view, "__globals__", {})` (see `ninja.signature.utils.get_typed_signature`). It uses the wrapper's `__globals__` for forward-ref resolution, not the wrapped function's. A `@functools.wraps` wrapper carries the _decorator module's_ globals (e.g. `core/authz/markers.py`), so Ninja fails to resolve any annotation that lives in the wrapped function's module — most importantly, closure-scoped types in factory-built CRUD views (`data: request_body_schema` in `entity_crud.py`). The error surfaces as a pydantic `class-not-fully-defined` panic at OpenAPI generation, not at decoration time, so the decorator can sit in the codebase passing tests until the next `make api-gen`.

The fix is to rebuild the wrapper as a `types.FunctionType` carrying the wrapped function's `__globals__` while preserving the closure cells the body needs:

```python
def template(request, *args, **kwargs):
    _enforce(request.user, activity)   # closure cell
    return func(request, *args, **kwargs)

wrapper = types.FunctionType(
    template.__code__,
    func.__globals__,                   # the load-bearing swap
    name=template.__name__,
    argdefs=template.__defaults__,
    closure=template.__closure__,
)
functools.update_wrapper(wrapper, func) # copies __wrapped__/__signature__/etc.
```

Module globals referenced by the body (like `enforce`) must be captured as closure cells (`_enforce = enforce` in the enclosing scope) — once `__globals__` is the wrapped function's, the body's `LOAD_GLOBAL` lookups happen against it, and `enforce` isn't there.

`markers.py:requires` is the reference implementation. When a second wrapping decorator lands, extract a shared `wrap_view_preserving_globals(template, func)` helper at that point — not before.

### Documented exception: inline `check()`

A small set of routes legitimately can't fit the single-decorator form — they evaluate multiple activities, branch on the decision, or need to run the check after mutation-context loading. These call `check()` inline, but **carry an explicit marker** so the inventory test still recognizes them as gated:

```python
@router.post("/claims/{id}/revert", auth=session_auth)
@gated_inline(Activity.CLAIM_REVERT)
def revert_claim(request, id: int, ...):
    claim = get_object_or_404(Claim, id=id)
    decision = check(request.user, Activity.CLAIM_REVERT, target=claim)
    if isinstance(decision, Deny): raise PolicyDenied(decision)
    ...
```

The `@gated_inline` decorator is informational — it does not run the policy itself (the inline `check()` does that). Its only job is to declare the activity to the inventory test. Inline gating is the exception, not the default; if a route can use `@requires()`, it should.

### Public-mutation allowlist

Some mutating routes legitimately have no activity gate — anonymous signup, password reset, contact form. Being ungated is a positive declaration, not the absence of one:

```python
@router.post("/auth/signup", auth=None)
@public_mutation("anonymous account creation by design")
def signup(request, ...): ...
```

`@public_mutation(reason)` records the route in the inventory as deliberately-public; the reason string is captured in the inventory output so a future reviewer can audit "do we still want this public?"

### Route-inventory test

A pytest walks every Ninja router in the project and classifies each mutating operation by the markers above:

- `@requires(Activity.X)` decorator → gated, mapped to `X`
- `@gated_inline(Activity.X)` decorator → gated, mapped to `X` (manual `check()` in body)
- `@public_mutation(reason)` decorator → deliberately ungated, with reason captured
- none of the above → **test failure**, with the route path in the message

A mutating route that lacks any marker fails the test. There is no `# noqa`. The list of activities the test recognizes is read from the central registry, so the test and the policy share one source of truth.

## Surfaces to classify

Every authenticated mutating backend route must carry one of the markers above (`@requires`, `@gated_inline`, or `@public_mutation`). The inventory PR lands these markers as no-ops and the route-inventory test asserts the classification is exhaustive. Enforcement — flipping `@requires` from no-op to "call `policy.check` and raise on deny" — is a separate, later PR; until then, marker presence is the only commitment. See [Implementation phases](#implementation-phases) below.

Known surfaces include:

- catalog claim writes
- catalog creates, deletes, and restores
- claim revert and changeset undo
- media upload, detach, category, and primary-image mutations
- citation source, link, extraction, and citation-instance mutations
- kiosk config mutations
- factory-registered CRUD routes

Keep the exhaustive route inventory in code or tests, not this document, so it can be mechanically checked instead of going stale.

## Implementation phases

The design ships across a sequence of small PRs. Each is independently mergeable; the first three are intentionally no-ops on user-visible behavior, and from Phase 4 onward each phase lights up one specific user-facing change (email gate, denial copy, target-less affordances, per-row affordances).

Each PR's acceptance criterion is small enough to bisect cleanly: PR 1 is "inventory test passes," PR 2 is "engine unit tests pass," PR 3 is "every authenticated user can still do everything they could yesterday," and so on.

### 1. ✅ DONE: Inventory + markers (no enforcement)

Add `@requires`, `@gated_inline`, `@public_mutation` as marker-only no-ops in `core/authz/`. Apply across every mutating route. Land the route-inventory test that asserts every mutating operation carries one of the three markers. No engine module yet; no behavior change.

### 2. ✅ DONE: Engine module

Build `core/authz/` proper: `Decision` / `Allow` / `Deny`, `DenialCode` enum, registry, predicate composition, `PolicyUser` Protocol, evaluator, and per-app `authz.py` rule files registering each launch activity with `authenticated + active` rules. Pure unit tests, no integration. `@requires` is still a no-op; `policy.check` exists but nothing calls it from a request path.

### 3. ✅ DONE: Enforcement flip

Update `@requires`'s body to call `policy.check` and raise a structured 403 on deny. (`@gated_inline` stays stamp-only — its routes already call `check()` inline; flipping the marker would double-evaluate.) Launch rules are still `authenticated + active`, so behavior is unchanged from today (every authenticated user passes). This is the moment "the gate is on" with zero user-visible diff.

### 4. ✅ DONE: Email verification gate

([Verification.md](Verification.md)). Add `email_verified` column to `User`, wire it into the mirrored-fields refresh, add the `email_verified` predicate to each launch activity's rule. Now the gate actually slows spam.

### 5. Denial-code mapper + resend-verification UI

Frontend-only. Add the `code → { title, body, primaryAction }` mapper module that the SPA's render layer consults, layered on top of `parse-api-error.ts` (the parser keeps its job of "extract a message string"). Wire the resend-verification flow for the `verification_required` code. No new backend endpoints; this lights up consistent copy across every editor for failures already happening since Phase 4.

**Scope: only `verification_required` gets real copy.** That's the only denial code the policy can actually surface as a 403 today. Every gated mutating route uses `auth=django_auth`, and Django's auth backend filters on `is_active=True` (see `apps/accounts/backends.py`), so an inactive user 401s before `@requires` runs — `account_deactivated` has no producer on a request path. `auth_required` likewise can only fire on a route whose `auth=` permits anonymous and then calls `policy.check`; no such route exists today. Both codes matter for `/me/capabilities` (Phase 7), not for 403 rendering, so their mapper entries land as stubs here (returning the backend's `message` fallback) and get real copy in Phase 7 when they start firing for real. `role_required` and `rate_limited` aren't emitted by any current call site, and `account_banned` doesn't exist yet; their mapper entries land with the phases that introduce them (6a/6c for the role and rate-limit codes, the future banning work for `account_banned`). Building the full table now would be premature — the copy needs review per code, and reviewing copy for codes nothing fires is wasted cycles.

Pulled ahead of the role-predicate work so the highest-volume new denial code from Phase 4 stops falling through to the plain-message fallback as soon as possible.

**Backend prerequisite: the resend-verification endpoint.** Phase 4 shipped the `email_verified` field and predicate but did not ship the resend endpoint that [Verification.md](Verification.md) names as its own — `apps/accounts/api.py` has no `send_verification_email` route today. The resend button in this phase has nothing to call without it, so this phase pulls in the endpoint: a session-authenticated POST that calls `client.user_management.send_verification_email(user_id=request.user.workos_user_id)` and returns 204. Frontend-only is therefore a misnomer for the PR as a whole; the SPA work is frontend-only, but the PR also ships the backend endpoint.

### ✅ DONE: 6a. Role predicates

Add `is_staff` and `is_superuser` predicates to `core/authz/predicates.py` with the `role_required` denial code (already in the priority list). Foundational only — no call sites consume them yet, so behavior is unchanged. Lands as its own commit so the predicate API can be reviewed without being bundled with the kiosk and rate-limit refactors that depend on it.

### ✅ DONE: 6b. Kiosk: fold superuser check into the policy

Fold `is_superuser` into `KIOSK_EDIT`'s rule; remove the inline `_require_superuser` helper from `apps/kiosk/api/configs.py`. Behavior unchanged — the policy verdict matches the inline helper.

### 6c. Rate-limit exemption via the policy

Add a `rate_limit.exempt` activity registered with `is_staff`. Update `provenance/rate_limits.py` to call `policy.check(user, Activity.RATE_LIMIT_EXEMPT)` instead of reading `user.is_staff` directly. After this, the rate limiter never reads role flags directly — the policy is the single source of truth for _who qualifies_.

Update the module docstring at the top of `rate_limits.py` (currently "Staff (`user.is_staff`) bypass all limits") to describe the new mechanism — exemption is decided by `rate_limit.exempt`, which today resolves to `is_staff` but is no longer the file's concern. A reader who learns the mechanism from the docstring should not then go looking for `is_staff` reads in this file.

`rate_limit.exempt` happens to have no route and no current UI consumer, but it's a plain Activity with no special-case flag. The route-inventory test walks routes → registry, not the reverse, so an activity without a route causes no failure. `/me/capabilities` returns it like any other; the SPA ignores capabilities it doesn't consult, and a future client could legitimately use this verdict to skip optimistic-throttle UI. If a future activity ever needs to be hidden from `/me/capabilities` for a substantive reason (e.g. a sensitive-moderation activity whose existence in the response would leak info), add the filter then.

#### Scope notes for Phase 6 (a/b/c)

`AuthStatusSchema.is_superuser` and the `is_superuser` redirect in `frontend/src/routes/kiosk/edit/+layout.server.ts` remain until Phase 7 lands `/me/capabilities` — removing them earlier would leave the SPA without a signal for the kiosk-edit affordance.

Out of scope: the `is_staff`/`is_superuser` check in `accounts/api.py` WorkOS auto-link (a privilege-hijack safety guard, not a permission gate — stays as raw flag checks).

### 7. /me/capabilities + AuthStatusSchema cleanup

Backend + frontend changes for the target-less capabilities surface. Add `/me/capabilities` returning the verdict for each non-internal target-less activity. Anonymous callers get everything-false (per "anonymous users go through the policy").

**New activity: `django_admin.access`** (rule: `is_staff`). Django admin's `/admin/` is staff-gated by the framework itself; this activity exists so the SPA can decide whether to render the "Django Admin" nav link without the schema needing to expose the underlying flag. The activity is named for the surface it gates, not the role permitted (see ["Activities are named for what's being gated, not who can do it"](#principles)).

Migrate every frontend `is_superuser` consumer to a capability, then drop the field from `AuthStatusSchema` entirely:

- `frontend/src/routes/kiosk/edit/+layout.server.ts` — switch the redirect to consult `kiosk.edit` from `/me/capabilities`.
- `frontend/src/lib/components/Nav.svelte` — the desktop and mobile menus both gate an `adminSection` snippet on `auth.isSuperuser` to show a "Kiosks" link (→ `/kiosk/edit`) and a "Django Admin" link (→ `/admin/`). Migrate per-link: "Kiosks" reads `kiosk.edit`, "Django Admin" reads `django_admin.access`. The section as a whole renders if either is allowed. This is what makes `django_admin.access` worth introducing — without it, dropping `is_superuser` from the schema would force the Nav to keep reading some other flag for the Django admin row.
- `frontend/src/lib/auth.svelte.ts` — the `auth` store's `isSuperuser` field and `set()` parameter both go away. Update before consumers so the type system catches missed call sites; the store is the _first_ file to edit, the schema field removal is the last.
- `frontend/src/lib/components/Nav.dom.test.ts` and `frontend/src/routes/kiosk/edit/layout-server.test.ts` — update fixtures to drive capability state instead of `is_superuser`. Lockstep with the components they exercise.

**Audit before removing the schema field.** After the named migrations land, grep `frontend/` once more for any remaining `is_superuser` / `isSuperuser` read; the audit's output (each found read + its disposition) is part of the PR description. The named migrations cover the consumers known today; the audit catches anything that's slipped in since this plan was written.

This is the phase that lets target-less affordances (create buttons, top-level New entries, Nav rows) gate on policy verdicts instead of role flags or "are they logged in."

### 8. Embedded per-resource capability hints

The first phase that introduces target-aware rules. Adds per-resource capability fields to serializers for target-aware activities (e.g. `claim.revert` on a claim, `catalog.delete` on an entity). Ships:

- The first per-target Protocols and predicates (`ClaimPolicyView`, `is_claim_author`, `claim_not_locked`).
- The `assert_predicate_is_pure(predicate, user, target, context)` test helper, designed against the target-aware shape (see [Verifying purity in tests](#verifying-purity-in-tests)).
- Embedded-hint fields on the affected resource serializers, reading verdicts via `policy.check(...)` per row.

`changeset.undo` is target-aware (the activities table notes it's "scoped to the changeset author") but is **not** part of this phase. It rides along with the per-target work the next time the post-delete Undo flow needs touching, or sooner if a stakeholder asks for the per-row affordance — the embedded hint requires the same Protocol/prefetch pattern this phase establishes for `claim.revert`, so it's mechanical once the pattern is in place. Listed here so it doesn't get lost.

**Each serializer audit must include a prefetch checklist.** The policy reads attributes off already-loaded objects, so any serializer that embeds a hint must `select_related` / `only(...)` the attributes the relevant `*PolicyView` Protocol declares, or the embed loop will N+1 behind the policy's back. Grep the Protocol to find the exact attribute list per target. A query-count regression test on each affected list endpoint is the dynamic backstop.

### 9. Observability

Stand up a denial-rate dashboard keyed off the audit-log records emitted since Phase 3 (`(user_id, activity, code, target_id)`). Group by `activity` and `code` so that an unexpected cohort hitting `verification_required`, a route that started 403'ing after a rule tightened, or a sudden `role_required` spike are all visible without trawling logs. Lands last because earlier phases are what _generate_ the signal worth watching; running this earlier would dashboard a near-empty stream.

The dashboard is the on-call backstop for any future rule tightening (account-age, reputation, rate-limit-as-policy) — those changes are easier to ship safely once denial rates are observable in aggregate. This is also the natural place to revisit whether dry-run mode (currently deferred) is worth building before the next rule change.

### 10. Documentation

Document the authorization surface area for future contributors and agents. Likely a new `docs/Authz.md` covering the system as it exists post-rollout, plus targeted additions to `docs/AGENTS.src.md` (which regenerates `CLAUDE.md` / `AGENTS.md`). Scope to be fleshed out closer to implementation — by then, the shape of what's load-bearing vs. obvious-from-code will be clearer.

## Deferred / non-goals

- **Dry-run mode for rule changes.** Once the launch rules are in place, tightening one (e.g. adding an account-age requirement to `catalog.create`) risks 403'ing active users mid-session. The usual answer is a dry-run pass that returns the would-be decision in a header without enforcing, then flip after one deploy cycle. Not needed pre-launch; the pure-decision design makes this easy to add later.
- **Bulk / batch evaluation API.** Per-target capability hints in list responses are 50× `policy.check` calls per render. With pure decisions and prefetched attributes that's cheap; if a profiler ever disagrees, add a `check_many` helper. Not worth designing speculatively.
- **External authorization engine** (OPA, Cedar, Oso). The shape of this design is compatible with a future port, but the in-repo policy module is the right size for Flipcommons today.

## Alternatives considered

- **django-rules.** The closest existing fit in the Python/Django ecosystem: predicate-based, composable with `&` / `|` / `~`, default-deny, object-level support, pure-function model. Maps onto most of the principles above. Rejected because it returns `bool`, so the structured-decision contract — typed `Decision`, denial-code priority order, per-code `context` shape — would have to be built as a wrapper of comparable size to writing the engine ourselves. Secondary concern: the natural call site (`user.has_perm("catalog.edit")`) reads as Django's permission framework even though django-rules sidesteps the underlying `ContentType` machinery, which invites the confusion we're explicitly trying to avoid. A ~150-LOC in-repo module is the simpler answer at our scale.
- **django-guardian.** Per-object permissions via DB rows. Wrong shape — our launch rules are attribute checks (verified email, active account), not row-level grants, and persisting per-(user, object) rows would be a denormalized mirror of attributes that already live on the user.
- **Casbin / py-abac / Vakt.** General-purpose RBAC/ABAC engines with external policy files or DSLs. Heavier than the problem; the policy file becomes a second source of truth that has to stay in sync with the activity registry.
- **Oso (open-source).** Was the obvious pick a few years ago; the company has deprioritized the OSS library in favor of a hosted product. Not a stable bet.
- **Django's built-in permission framework + `ContentType` perms.** Already excluded by a principle above; restated here for completeness — per-model perms compose poorly with attribute checks, and we'd end up wrapping them.
