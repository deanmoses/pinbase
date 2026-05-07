# Custom User Model

This document proposes implementing a custom user model.

## Status - DONE

Implemented May 7 2026.

## Related work

This is the first step of an auth-hardening sequence. After this lands, follow-on plans build on the model shape defined here: [Webhooks.md](Webhooks.md) + [Verification.md](Verification.md), then [UserSelfManagement.md](UserSelfManagement.md).

## Problem

This project is pre-launch, and we've deferred the question of how to manage users until now. We're on Django's default `auth.User`, but Django's default `User` is starting to bend under our requirements:

- **No way to enforce email uniqueness cleanly.** `auth.User.email` is `blank=True, unique=False`. The matching logic in `get_or_create_django_user()` (`apps/accounts/api.py:111`) compensates, but only when there's exactly 0 or 1 match — 2+ matches silently create a duplicate user. We need a partial-unique constraint that the default model can't carry.
- **The pending auth-hardening fields don't have a clean home.** [Verification.md](Verification.md) introduces `email_verified`; the provider-switching freshness signal `last_seen_at` needs somewhere to live too. With default `auth.User`, every such field has to land on the existing `UserProfile` sidecar — which makes every read of basic identity state go through `select_related("profile")`.

## Using a custom user model

Django's official guidance is to define a custom user model from day one of any project. Doing it later is famously painful — but the project hasn't launched, so we don't have to migrate; instead, we will drop the DB and re-ingest. The user has confirmed this is acceptable.

## Proposed model

A new `accounts.User(AbstractUser)`. The existing `UserProfile` model is dropped; its two fields (`workos_user_id`, `priority`) move onto `User`.

### `accounts.User`

```python
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import field_not_blank


class User(AbstractUser):
    # AbstractUser provides:
    #   username, first_name, last_name, email,
    #   is_active, is_staff, is_superuser, last_login, date_joined, password
    #
    # `username` is left bone-standard (AbstractUser's CharField with
    # UnicodeUsernameValidator). It's user-editable and serves as the public
    # URL slug (/users/<username>). Defaulted from the email prefix at first
    # login via _generate_username(). Editable on the settings page per
    # UserSelfManagement.md.

    # Redeclared only to flip AbstractUser's blank=True to blank=False, so
    # admin/form validation rejects empty emails cleanly instead of bouncing
    # off the DB CHECK as a 500. Case-insensitive uniqueness is enforced by
    # the Lower("email") UniqueConstraint in Meta below — not by unique=True
    # on the field, which would only catch byte-for-byte duplicates. Casing
    # is preserved on save by the manager (not lowercased), so we display
    # what the user typed. Soft-deleted users keep their email for
    # reactivation lookup (see notes below).
    email = models.EmailField()

    # --- Identity / auth-state (gates access) ---

    # Pointer to the WorkOS-side user row — the managed-provider link. When we
    # switch managed providers, this column becomes legacy and a new
    # clerk_user_id (or generalized column) takes its place.
    #
    # null=True only for the soft-delete window: the Webhooks.md user.deleted
    # handler clears workos_user_id (so a returning user can re-bind to this
    # row at reactivation time, see notes below). Active and never-active rows
    # both carry a value. The nullability is load-bearing for the soft-delete
    # contract, not an open invariant.
    workos_user_id = models.CharField(max_length=64, null=True, blank=True, unique=True)

    # Request-time freshness signal (see ProviderSwitching.md).
    last_seen_at = models.DateTimeField(null=True, blank=True)

    # --- On-site profile ---

    # Wikipedia-style attribution priority (existing field, moved off UserProfile).
    priority = models.PositiveSmallIntegerField(default=10000)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # createsuperuser will prompt for email + password only.

    class Meta:
        constraints = [
            # Case-insensitive unique email — Alice@... and alice@... collide.
            # Functional index works on PostgreSQL and modern SQLite.
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_unique_email_ci",
            ),
            # Email must be non-empty.
            field_not_blank("email"),
            # workos_user_id may be NULL, but if set, may not be empty string.
            field_not_blank("workos_user_id"),
        ]
```

Notes on the choices:

- **`USERNAME_FIELD = "email"`.** The OIDC canonical identifier is `sub`, not email — but `sub` is opaque and provider-scoped, so we link it via `workos_user_id`, not as the login key. Email is the human-readable identifier every provider returns and the natural login key on our side.
- **One slug: `username`, user-editable, used as the URL slug.** With `USERNAME_FIELD = "email"`, Django's `username` is freed from being the login identifier; we keep it as the single user-facing slug (`/users/<username>`). Defaulted from the email prefix via `_generate_username()` at first login, editable on the settings page (per [UserSelfManagement.md](UserSelfManagement.md)). A separate immutable internal handle was considered and rejected as folkloric — third-party Django packages key off `user_id` (FK), not the username string, and our own logging/audit code does the same. The one residual cost is that historical log strings like `f"user={user.username}"` become ambiguous after a rename; mitigation is to log `user_id` everywhere, which is best practice anyway.
- **`workos_user_id` is on `User`.** It's identity, not preference — it determines which row a sign-in maps to. It's the managed-provider pointer; capturing the underlying OAuth `sub` is a separate concern (see [SocialAccountSync.md](SocialAccountSync.md)).
- **Full-unique email + reactivation on signup.** One row per email, ever. When a returning user signs in via WorkOS — they got a new `workos_user_id` because they closed and recreated their auth account — `get_or_create_django_user()` matches the soft-deleted row by email and reactivates it (`is_active=True`, re-bind `workos_user_id`, update `last_seen_at`). They keep their contribution history; we don't silently fork their identity into a second row. The alternative (partial-unique on `is_active`) was considered and rejected: it lets the new signup quietly create a fresh row, stranding the old contributions on the soft-deleted row.
- **Reactivation gate — required from day one.** Reactivation is a privilege escalation in disguise (it inherits the prior user's contribution history), so it must be gated. The check:

  **`auth_response.user.email_verified` must be true.** Without this, an attacker registers victim@oldcompany.com via the email/password path and inherits Alice's history before WorkOS sends the verification email. We don't need the local `email_verified` field yet (that's deferred to [Verification.md](Verification.md)) — the inbound login already carries the verified flag on the WorkOS user object. It's a non-Optional `bool` on the SDK `User` model (`workos/types/user_management/user.py`), so present on every authenticated user; already read at `apps/accounts/api.py:129` in the existing flow. WorkOS sets it `True` after social-OAuth login (the upstream provider has verified) and `False` for password sign-ups until the verification email is clicked. Read it live; don't reactivate if false.

  Concretely, the reactivation predicate is `is_active=False AND inbound.email_verified=True`. If the clause fails, fall through to "refuse" — never silently reactivate.

  Two further clauses are deferred:
  - **"inbound OAuth `(provider, sub)` matches a stored identity"** — catches the corporate-email-reassignment case (Alice leaves, Bob inherits `alice@oldcompany.com`, signs in via SSO). Deferred along with the `SocialAccount` model to [SocialAccountSync.md](SocialAccountSync.md).
  - **"`banned_at` must be NULL"** — needed once moderation bans exist, otherwise banning is reversible by signing out and back in. Deferred to [UserBanning.md](UserBanning.md). Until that lands, an admin can disable a user via `is_active=False`, accepting that a determined returning user could trigger reactivation through signup; we don't yet have abusive users to defend against.

- **Soft-delete preserves email.** The [Webhooks.md](Webhooks.md) `user.deleted` handler sets `is_active=False` and clears `workos_user_id`, but **does not** clear `email` — clearing it would make reactivation impossible (no key to match on). If we ever get a hard GDPR-erasure request, that's a separate management-command path that fully purges the row.
- **Email normalization — domain only, RFC-respecting.** The custom `UserManager` (Migration step 4) calls `BaseUserManager.normalize_email()` from Django, which lowercases the _domain_ but preserves the _local-part_. RFC 5321 says the local-part is technically case-sensitive — no real mail provider honors this, but preserving casing means we display `Alice.Smith@example.com` the way she typed it. Uniqueness is enforced case-insensitively by the `Lower("email")` functional index in `Meta`, so `Alice@...` still collides with `alice@...` at the constraint level. Reactivation lookup uses `email__iexact` for the same reason — case-insensitive matching against stored case-preserved values. Per the [DataModeling.md](../../DataModeling.md) "validate in the database" principle, the functional index is the DB-level enforcement that bulk-insert / `update()` / raw SQL / migrations can't bypass.
- **No generic `updated_at` for v1.** Considered and dropped — every event we'd want to capture already has a more specific timestamp (`last_login`, `last_seen_at`, `date_joined`), and the user-editable fields whose "last touched" would warrant a generic column (bio, avatar, display name) are deferred to UserSelfManagement.md. Add `updated_at` then, when there's something worth tracking generically.

## What this lets us delete

Things that exist today only because we don't have a custom user model:

- **`UserProfile` itself.** Drop the model, the related-name lookups, the inline in `accounts/admin.py`, the schema in `accounts/api.py`. Every reference to `user.profile.X` becomes `user.X`.
- The `_get_profile()` helper (`api.py:107`) — gone with `UserProfile`.
- The `matches.count() == 1` ambiguity branch in `get_or_create_django_user()` (`api.py:129`). Becomes impossible by construction with the full-unique email constraint — at most one row matches; reactivate it if soft-deleted, otherwise create. (`_generate_username()` itself stays unchanged — same derivation logic, now seeding the single `username` field.)
- `from django.contrib.auth.models import User as DjangoUser` (`api.py:13`). Replace with `from apps.accounts.models import User`.
- `from django.contrib.auth.models import User` in `apps/media/tests/test_upload_api.py:9`. Replace with `get_user_model()` (this one's an existing bug — should never have referenced the model directly).

## Migration

The user has confirmed dropping the prod DB and re-running `make pull-ingest && make ingest` is acceptable. That makes this a green-field migration in everything but name.

### Steps

Note on intermediate states: this is a single-PR migration. The tree won't compile at every intermediate step — some imports reference classes that don't exist yet, and `AUTH_USER_MODEL` isn't set until step 3. The end state compiles; that's what matters. Don't try to land these as separate commits expecting each to be green.

1. **Create `apps/accounts/models.py: User(AbstractUser)`** as specified above. Delete the existing `UserProfile` model in the same change. (Done first because subsequent steps reference the new class.)
2. **Set `AUTH_USER_MODEL = "accounts.User"`** in `config/settings.py`.
3. **Custom `UserManager`** with a `create_user(email, password=None, **extra)` that calls `self.normalize_email(email)` (Django's built-in — lowercases domain, preserves local-part) and seeds `username` from `_generate_username()`. Required because `AbstractUser`'s default manager expects the caller to supply `username`, but we want it derived from email.
4. **Audit and rewrite every direct `auth.models.User` reference.** Most of the codebase uses `settings.AUTH_USER_MODEL` or `get_user_model()` (good); the rest will silently keep referring to the _old_ `auth.User` after the swap and produce confusing test failures. Don't enumerate by hand — run the grep:

   ```bash
   rg -n "from django\.contrib\.auth\.models import.*\bUser\b|django\.contrib\.auth\.models\.User|auth\.models\.User" backend/
   ```

   At time of writing this hits ~10 files across `apps/accounts/`, `apps/provenance/`, `apps/core/`, and `apps/media/`. Rewrite each:
   - In `apps/accounts/models.py` (the new home): leave alone — the new `User` class lives here.
   - In application code: replace with `from apps.accounts.models import User` (preferred when type-annotating model FKs / signals) or `get_user_model()` (preferred at module-level helpers and tests).
   - In `models.py` files anywhere: never import the model directly for FKs — use `settings.AUTH_USER_MODEL` as a string. The grep should come up clean for FKs after this pass.
   - Re-run the grep after the rewrite to confirm zero hits outside `apps/accounts/models.py`.

5. **Remove existing migrations from a clean slate.** Since we're dropping the DB:
   - **First, audit for `RunPython` / `RunSQL` operations.** Grep `backend/apps/*/migrations/` for non-trivial data migrations — default-row inserts, backfills, constraint repair, anything that encodes behavior the schema alone doesn't carry. `provenance`, `catalog`, and `core` are the likely sites. Port any such logic into a fresh data migration before deleting the originals; otherwise it's lost silently.
   - Delete every app's `migrations/00*.py` files (keep `__init__.py`).
   - Run `make migrate-fresh` (or equivalent) to regenerate all migrations against the new user model.
   - Re-run `make ingest` to repopulate catalog data.
6. **Update `apps/accounts/admin.py`** to register the custom user model with a custom `UserAdmin` (Django requires this; the default `auth.UserAdmin` has hardcoded references to `username` as the login field). Drop the `UserProfileInline`. `is_active` stays editable — admins can disable users by toggling it (moderation bans with their own column and audit trail are deferred to [UserBanning.md](UserBanning.md)).
7. **Update `apps/accounts/api.py`:**
   - `_generate_username` derives from the email prefix as today (lowercase, replace `.` / `_` / `+` with `-`, strip anything outside `[a-z0-9-]`, collapse repeated hyphens, trim leading/trailing hyphens) — produces a clean URL-safe default that's narrower than the bone-standard `UnicodeUsernameValidator` allows but well within it. Wrap the existing `.exists()` collision loop with a single retry-on-`IntegrityError` (TOCTOU race: two concurrent first-logins both pick `alice`, one fails the unique index — re-run the loop once with a fresh `.exists()` check, which will now find the winner's row and pick the next suffix). If the retry also fails, propagate.
   - `get_or_create_django_user` simplifies and gains gated reactivation. The inbound payload is `auth_response.user`. Four branches:
     1. **Lookup by `workos_user_id`.** If found and `is_active=True` → refresh mirrored fields (see below), return. If found but inactive → refuse the login.
     2. **Else lookup by `email__iexact`** (active or soft-deleted). If found and reactivation guards all pass — `is_active=False` _and_ `inbound.email_verified=True` — reactivate (`is_active=True`, re-bind `workos_user_id`, refresh mirrored fields, save) and return.
     3. **Else if found by email but the guard failed** (unverified inbound email) → refuse the login with a clear error; do not silently create a new row, since that would orphan the old contributions.
     4. **Else create a new user** via the manager. Wrap in `IntegrityError` retry-by-re-lookup: two simultaneous first-logins for the same email both miss the lookup, both `INSERT`, one wins the unique index — the loser re-runs the lookup and proceeds via branches 1–3. The same handler also catches the "two WorkOS accounts claim the same local user" case: a `workos_user_id` collision on insert means we tried to bind an `id` that's already on a different active row. Log at error level ("two WorkOS accounts claim same local user, refusing login until admin resolves") and refuse — surface it loudly so a human can untangle.

     Drop the `count() == 1` ambiguity path and the `_get_profile()` call.

   - **Mirrored fields, explicitly.** "Refresh mirrored fields" means: `email`, `first_name`, `last_name` — copied verbatim from `auth_response.user`. That's the v1 list; `email_verified` joins it when [Verification.md](Verification.md) lands. Save with `update_fields=["email", "first_name", "last_name"]` so `last_login` (handled by Django's signal) and any future `updated_at` aren't disturbed.
   - **Email-change re-verification.** When a webhook (or a future settings-page edit) changes a user's email, `email_verified` flips back to false until the new address is re-verified. Owned by [Verification.md](Verification.md); flagged here so it doesn't fall through.
   - `UserProfileSchema` and any `user.profile.X` reads collapse to fields on `user`.
   - `auth_me` and `user_profile_page` route by `username` — it's the public URL slug. `user_profile_page` accepts a `username` URL kwarg and looks up by that field.

8. **Update `apps/accounts/signals.py`** if it has a `post_save` profile-creation hook — delete it; there's no profile to create.
9. **Update `apps/accounts/backends.py: WorkOSBackend.get_user()`** to refuse inactive users:

   ```python
   def get_user(self, user_id):
       try:
           return User.objects.get(pk=user_id, is_active=True)
       except User.DoesNotExist:
           return None
   ```

   Defense in depth: `get_user()` runs on every authenticated request via `AuthenticationMiddleware`, so a user who's been disabled (`is_active=False`) stops being authenticated on the very next request, with no need to flush sessions. ([UserBanning.md](UserBanning.md) tightens this further with a `banned_at__isnull=True` filter when moderation bans land.)

10. **Add a middleware to populate `last_seen_at`.** Without a writer, the column stays NULL forever and provides no value at provider-switch time — the whole point is to have the value accumulating now. Shape:
    - **Guard on `request.user.is_authenticated` first.** For unauthenticated requests `request.user` is `AnonymousUser`, which has no `last_seen_at` attribute and would `AttributeError`. Skip the rest of the middleware in that case.
    - **Debounce to once per day per user, using the stored field value as the debounce state** — read `request.user.last_seen_at` (already loaded by `AuthenticationMiddleware` for authenticated users, no extra SELECT) and skip the UPDATE if it's within the last 24h.
    - Don't keep an in-memory `{user_id: last_write}` cache: that resets on every server restart and would spike a write per active user at boot.
    - Wire the middleware into `MIDDLEWARE` in `config/settings.py` after `AuthenticationMiddleware`.
    - Leave a `# TODO(perf):` at the UPDATE call site noting that under traffic this should move off the request path (`transaction.on_commit` or a queue). At v1 scale it's fine; the TODO is for future-grep when it isn't.
11. **Update tests.** Anything that does `User.objects.create_user(username="...")` needs to switch to `email=...`. Anything that asserts on `user.profile.X` becomes `user.X`.
12. **Update `apps/accounts/test_factories.py`** (and provenance test factories) to construct users via the new manager and drop `UserProfile` factory usage.

### Migration is one-way

We're not building a backwards path. Once migrations regenerate and the dev DB is re-seeded, there's no "switch back to `auth.User`" scenario worth supporting. Branch this work, prove it green, merge.

### Coordinating with other open auth plans

Several in-flight plan docs assume the old shape (default `auth.User` + `UserProfile` sidecar). After landing this:

- **[Verification.md](Verification.md)** — proposed `UserProfile.email_verified` lands as `User.email_verified`. The field is added by the Verification.md PR itself, not this one — it's read live from the provider on each login, so there's no accumulation reason to add it early. The `(provider, provider_sub)` external-identity table that Verification.md also proposed is split out and deferred — see [SocialAccountSync.md](SocialAccountSync.md).
- **[Webhooks.md](Webhooks.md)** — `profile.workos_user_id` collapses to `user.workos_user_id`. The proposed `is_banned` mirroring (Clerk-only `user.banned`/`user.unbanned` events) is deferred to [UserBanning.md](UserBanning.md); for v1 the webhook handler just sets `user.is_active=False`, with the same session-flush behavior. The flush-sessions helper still works (it walks `_auth_user_id`).
- **[ProviderSwitching.md](ProviderSwitching.md)** — `last_seen_at` lands on `User`. The provider-switching playbook is otherwise unaffected.
- **[UserSelfManagement.md](UserSelfManagement.md)** — the Field-by-Field Proposal table needs updating: the proposed `UserProfile.handle` collapses into the now-editable `User.username` (one slug, not two). All other proposed fields (`display_name_override`, `bio`, avatar fields, notification/privacy toggles) are out of scope for this PR — they land on `User` when UserSelfManagement.md actually ships, paired with the settings-page UI that consumes them. The "Why the username / handle split" section in that doc no longer applies and should be deleted in the follow-up sweep.

We don't need to update those docs in lockstep with this one — they describe the target shape, and once the custom user lands, the field locations drift in the obvious way. A single follow-up commit can sweep them.

## Open questions

- **When (if ever) does a sidecar earn its keep?** Not now. The trigger would be a real role distinction (`MuseumStaff`, `Volunteer`, `Editor` with permissions) — at which point we'd add a Flipfix-`Maintainer`-style model alongside `User`, not split user fields out of it.

## Non-goals

- **Roles / permissions / trust tiers.** This doc adds the model; the authorization design is its own future doc.
- **Account merge for the same human across two providers.** Future doc.
- **Custom `AbstractBaseUser` (vs. `AbstractUser`).** The smaller leap; we lose nothing by keeping `AbstractUser`'s built-ins.
- **Handle history table for 301 redirects.** Mentioned in UserSelfManagement.md as a future concern; out of scope here.
- **Mass user import from any existing data source.** There isn't a meaningful existing user base — Flipcommons hasn't launched. Re-ingest creates no users; users are created at first login.
