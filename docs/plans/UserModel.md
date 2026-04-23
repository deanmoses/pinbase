# Custom User Model

## Problem

This project uses `django.contrib.auth.models.User` directly — we have no custom User model and no `AUTH_USER_MODEL` override. There is an `apps.accounts.UserProfile` OneToOne sidecar, but the authenticated user class itself is Django's built-in.

Three pain points follow:

1. **Swapping the user model becomes harder every week.** Changing `AUTH_USER_MODEL` after tables exist is nearly unrecoverable in Django — every FK to the old `auth_user` table breaks, and data migration is a nightmare. FKs to `settings.AUTH_USER_MODEL` already exist in [citation/models.py](backend/apps/citation/models.py), [provenance/models/changeset.py](backend/apps/provenance/models/changeset.py), [provenance/models/claim.py](backend/apps/provenance/models/claim.py), [accounts/models.py](backend/apps/accounts/models.py), and [media/models.py](backend/apps/media/models.py). More accumulate over time.

2. **Typing gymnastics at FK write sites.** `request.user` is typed `AbstractBaseUser | AnonymousUser`, but FKs to `settings.AUTH_USER_MODEL` are typed against `auth.User`. Helpers like `execute_claims` / `execute_multi_entity_claims` in [catalog/api/edit_claims.py](backend/apps/catalog/api/edit_claims.py) end up with `cast(Any, user)` or `cast(User, user)` workarounds plus defensive `AnonymousUser` asserts. These casts can't be cleanly removed while `User` is a class we don't own.

3. **Tripwire on any future swap.** Code that imports `django.contrib.auth.models.User` directly for `isinstance` checks breaks at runtime if `AUTH_USER_MODEL` is later swapped — even though the FK would accept the new class. We have this pattern in at least `edit_claims.py` (after Step 4 cleanup) and `provenance/revert.py`.

Pinbase hasn't gone live. The DB is disposable. The window to fix this cleanly is now.

## Solution

Django's official recommendation for any new project: **define a custom User model from day one, even if you don't need customization yet.** The model is an empty subclass; it becomes the extension point you evolve over time, so the dreaded "swap `AUTH_USER_MODEL`" problem never actually needs to happen.

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    pass  # empty to start; fields/methods added as needed
```

```python
# settings.py
AUTH_USER_MODEL = "accounts.User"
```

Two base-class flavors:

- **`AbstractUser`** — inherits username, email, first/last name, `is_staff`, password, groups, permissions. A straight rename of the default. Use when the default shape is roughly right.
- **`AbstractBaseUser + PermissionsMixin`** — no predefined fields except password. Use for email-as-username, multi-tenant, or anything exotic. Forces more up-front design.

For Pinbase, `AbstractUser` is the likely starting point — we already use username-based auth and the default admin/permissions plumbing.

### Why this fixes the three pain points

1. **"Swap" becomes "evolve."** You don't replace the user class — you modify the one you own. Need email-as-username later? Set `USERNAME_FIELD = "email"` on your `User`. Need a tenant column? Add a field and migrate. The `AUTH_USER_MODEL` pointer never moves, so the breakage scenario never occurs.

2. **Typing works cleanly.** `ChangeSet.user` (via `settings.AUTH_USER_MODEL = "accounts.User"`) is typed against the same class django-stubs resolves, so `ChangeSet.objects.create(user=user, ...)` accepts a narrowed `accounts.User` without a cast. Helpers can drop the `cast(Any, user)` / `cast(User, user)` workarounds. `assert isinstance(user, User)` (importing the project's own `User`) is now both runtime-correct and type-accurate, and stays correct across any future field additions.

3. **No tripwire.** The `User` you `isinstance`-check against is the same class every FK points at, by construction. Future evolution of the model doesn't invalidate existing checks.

### Migration posture

Since the database is disposable, the simplest path is: create the model, set `AUTH_USER_MODEL`, drop and recreate the DB (or delete migrations and regenerate). No preserve-rows data migration needed. Any already-created local superusers get recreated with `createsuperuser`.

Details — exact migration ordering, which tests/fixtures need updating, how to handle the existing `UserProfile` OneToOne (keep as sidecar vs. fold fields into `User`), admin registration, and any third-party package implications — are out of scope for this write-up and will be fleshed out in a follow-up session.
