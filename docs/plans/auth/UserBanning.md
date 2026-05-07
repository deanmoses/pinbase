# User Banning

This document proposes adding the ability for admins to ban users.

This would add moderation-ban state to `accounts.User` — distinct from the provider-soft-delete state that `is_active=False` already covers.

## Status — deferred

Deferred; revisit when one of the problems below becomes urgent. Until then, an admin can disable a user by toggling `is_active=False` in the Django admin — that blocks login (Django's `ModelBackend.user_can_authenticate()` honors it) and is reversible the same way. The cost is that a determined returning user could trigger reactivation through the signup flow and undo the disable; without abusive users to defend against, that's acceptable.

## Problem

**Bans need to survive reactivation.** [CustomUserModel.md](CustomUserModel.md) defines a reactivation path: a returning user whose `is_active=False` row matches by email gets `is_active=True` flipped back. That's the right behavior for users who deleted their auth account and came back, but it means that without a separate "banned" marker, banning is reversible by signing out and signing back in. The two states (provider-soft-delete vs. moderation-ban) need to be distinguishable on next login.

**Bans need an audit trail.** "Who banned this user, and when" is information moderators want before unbanning, and that we want to keep even after the banning admin's account is deleted.

**Defense in depth on the request path.** A freshly-banned user with a live session cookie should stop being authenticated on the very next request, not after their session expires.

## Proposed model additions

Two columns on `accounts.User`:

```python
# Moderation marker. NULL = not banned. Set when an admin (or future
# Clerk-style provider ban event) bans the user; we also flip is_active=False
# at the same time. The reactivation path on signup explicitly refuses rows
# with banned_at IS NOT NULL — without this column, banning is a sign-out-and
# -sign-back-in away from being undone.
banned_at = models.DateTimeField(null=True, blank=True)

# Who issued the ban. NULL = never banned, or banned by a provider event,
# or banner has since been deleted. SET_NULL because audit records outlive
# the actor.
banned_by = models.ForeignKey(
    "self",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="bans_issued",
)
```

Plus a Meta CHECK constraint:

```python
# Ban consistency: a banned user must not be active. Catches the
# admin-flips-is_active=True-while-banned_at-is-set footgun even
# though the admin UI funnels through actions; per DataModeling.md
# "validate in the database."
models.CheckConstraint(
    condition=Q(banned_at__isnull=True) | Q(is_active=False),
    name="accounts_user_banned_implies_inactive",
),
```

Notes:

- **`banned_at` distinguishes bans from provider-soft-deletes; everything else stays on `is_active`.** `is_active` is Django's canonical login gate (admin shows it, `ModelBackend.user_can_authenticate()` honors it). For both moderation bans and provider-`user.deleted` events we set `is_active=False`. The two are distinguished by whether `banned_at` is set — that's enough for the reactivation guard below. We deliberately don't add a separate `is_banned` boolean: the timestamp's nullness is the flag, and there's no second source of truth to drift.
- **`banned_reason` is deferred** until we actually have abusive users to annotate; the failure mode without it is a missing audit detail, not a correctness gap.

## Reactivation guard tightening

Add a clause to the `get_or_create_django_user` reactivation predicate (defined in [CustomUserModel.md](CustomUserModel.md)):

**`banned_at` must be NULL.** Otherwise banning is reversible by signing out and back in: ban → `is_active=False` → reactivation path flips it back to `True` and re-binds.

The predicate becomes `is_active=False AND banned_at IS NULL AND inbound.email_verified=True`. If the email matches a row but `banned_at` is set, refuse the login with a clear error — don't silently create a fresh row, since that would orphan the banned user's contributions.

## Admin

In `apps/accounts/admin.py`, add `ban_users` / `unban_users` admin actions that flip `is_active`, `banned_at`, and `banned_by` together:

- `ban_users` sets `banned_at=now`, `banned_by=request.user`, `is_active=False`
- `unban_users` clears `banned_at`/`banned_by` and sets `is_active=True`

Put `banned_at` and `banned_by` in `readonly_fields` so the actions are the _only_ path that can mutate them. Without that, an admin could set one without the others and produce a half-banned state. `is_active` itself stays editable — temporarily disabling a staff account is a legitimate use, and the worst an admin can do by accident is produce a soft-delete (a real distinct state), never a half-ban.

## Defense in depth — `WorkOSBackend.get_user()`

Tighten `apps/accounts/backends.py: WorkOSBackend.get_user()` to filter banned users out:

```python
def get_user(self, user_id):
    try:
        return User.objects.get(pk=user_id, is_active=True, banned_at__isnull=True)
    except User.DoesNotExist:
        return None
```

The login path (`get_or_create_django_user`) refuses banned users at signin, but `get_user()` runs on every authenticated request via `AuthenticationMiddleware`. Filtering here means a freshly-banned user with a live session cookie stops being authenticated on the very next request, with no need to flush sessions.

(In CustomUserModel.md's v1 shape, `get_user()` filters on `is_active=True` only — sufficient when there's no separate ban state.)

## Coordination with other auth plans

- **[CustomUserModel.md](CustomUserModel.md)** — defines the v1 reactivation predicate `is_active=False AND inbound.email_verified=True`. This doc adds the `banned_at` clause.
- **[Webhooks.md](Webhooks.md)** — the proposed `is_banned` mirroring (Clerk-only `user.banned`/`user.unbanned` events) wires into this model: handler sets `banned_at=now` and `is_active=False` together. Until this doc lands, the v1 webhook handler just sets `is_active=False` (see CustomUserModel.md coordination notes).

## Non-goals

- **Per-context bans (banned from comments but not edits).** Future doc; v1 is a single account-level ban.
- **Ban reasons / appeals workflow.** Future doc; v1 is action + audit-log.
- **Time-limited bans.** Future doc.
