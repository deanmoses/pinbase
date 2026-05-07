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
- `moderation.action`

Backend write paths should depend on activity authorization, not directly on `email_verified`. For example, a catalog claim write should require `catalog.edit`; the policy for `catalog.edit` can initially require authentication, an active account, and verified email. Later, the same policy can add account-age, role, reputation, moderation, or rate-limit constraints without changing every catalog editor.

The frontend should follow the same language but must not reimplement the policy. The backend exposes capabilities (e.g. a `/me/capabilities` endpoint, or per-resource hints embedded in resource responses) and the frontend reflects them for UX. Structured denial responses return stable blocker codes from a closed registry -- `verification_required`, `moderator_required`, etc. -- mapped to user-facing copy in one place, so shared UI can explain the problem without each editor knowing the underlying authorization rules.

This is the standard policy-based / capability-based authorization shape: call sites request an action, central policy evaluates roles and attributes. For Flipcommons, a lightweight in-repo policy module is enough; adopting a full external authorization engine would be premature.

## Principles

- **Object-level from day one.** The policy signature is `check(user, activity, target=None)`. Early rules may ignore `target`, but `claim.revert` and `catalog.delete` will need it soon, and retrofitting object-level later is the same costly audit this design is meant to avoid.
- **Backend is the source of truth; the frontend reflects.** Never mirror policy logic in JS. Two engines will drift.
- **Activities are product-meaningful, not data-model-shaped.** Resist granularity like `catalog.edit.title.scalar` -- that leaks the schema into the policy namespace and dissolves the abstraction.
- **Don't use Django's permission framework.** This activity layer is parallel to Django perms, not built on top. Per-model perms compose poorly with attribute checks (verified email, account age, rate limit), and we'd end up wrapping them anyway.
- **Denial codes are a closed enum.** One registry, mapped to user-facing copy. No ad-hoc strings spelled differently across editors.
- **Rate-limiting is policy-aware, not policy-owned.** Enforce early in the request path -- as early as the limit's scope allows (per-IP/per-user floods in middleware; activity- or target-scoped limits where the target is known). The policy may reflect rate-limit state for UX but is not the sole gate.

## Initial activities

The launch set. Each row is what the policy enforces today; later constraints (account age, reputation, rate limits, moderation flags) layer in without changing call sites.

| Activity            | Rules at launch                                     | Notes                                                                                                                                                                                                  |
| ------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `catalog.edit`      | authenticated, active, email-verified               | The default gate for claim writes on existing entities.                                                                                                                                                |
| `catalog.create`    | authenticated, active, email-verified               | Same bar as edit at launch; separated so creation can tighten independently (e.g. account age) without touching edit paths.                                                                            |
| `catalog.delete`    | authenticated, active, email-verified, target-aware | Object-level: deletion of a populated entity should escalate (moderator role) before non-moderator deletes are allowed. Launch behavior may simply forbid non-moderator deletes of non-empty entities. |
| `claim.revert`      | authenticated, active, email-verified, target-aware | Object-level: a user can revert their own claims; reverting another user's claim requires `moderation.action`.                                                                                         |
| `moderation.action` | authenticated, active, moderator role               | The umbrella capability for moderator-only operations. Email verification is implied by being a moderator.                                                                                             |

"Active" means the account is not disabled or banned. "Authenticated" means a logged-in session, not anonymous. The shared prerequisites (authenticated + active) live in one place in the policy module so each activity's rule is just the delta beyond them.

## Surfaces to classify before implementation

Before implementing the policy layer, audit every authenticated mutating backend route and assign it to one activity, or explicitly mark it out of scope.

Known surfaces include:

- catalog claim writes
- catalog creates, deletes, and restores
- claim revert and changeset undo
- media upload, detach, category, and primary-image mutations
- citation source, link, extraction, and citation-instance mutations
- kiosk config mutations
- factory-registered CRUD routes

Keep the exhaustive route inventory in code or tests, not this document, so it can be mechanically checked instead of going stale.
