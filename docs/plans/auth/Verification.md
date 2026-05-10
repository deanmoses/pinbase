# Email Verification Gate for Edits

## Problem

Flipcommons is a public, user-editable wiki. Anyone who completes the sign-up flow today can immediately make catalog edits. That's a spam vector: an attacker can register with a throwaway email-password account and start writing claims before they've proved they own the email address. We have no signal in the request path that distinguishes a verified human from a bot that just clicked through sign-up.

To combat this, edits should require a verified email. Social sign-ins (Google, Apple, GitHub, Microsoft) already prove email ownership at the IdP, so legitimate OAuth users should pass the gate without seeing it. Only the email-password sign-up path — the path a spammer would actually use — should be slowed down by "click the link we sent you."

We want to do this without coupling our domain code to WorkOS internals. Whatever we store should survive a migration to a new auth provider (Clerk, Auth0, self-hosted OIDC) -- see [ProviderSwitching.md](ProviderSwitching.md).

## Relationship to Authz.md

This document is about **landing the `email_verified` bit** on our side: where it lives, how it's refreshed from the IdP, and how the user gets it flipped to `true`. It is **not** about how write paths consume it.

The activity-authorization layer in [Authz.md](Authz.md) is the consumer. Backend write paths gate on activities like `catalog.edit`, not on `email_verified` directly; the policy for those activities is what reads this column. This split is deliberate — when the next constraint arrives (account age, reputation, role), call sites don't have to change. So:

- This doc owns: the field, the login-time refresh, the resend endpoint, the migration.
- Authz.md owns: the gate, the denial code, the per-activity rules.

## What `email_verified` actually means per provider

The WorkOS User object exposes a single `email_verified: bool` that abstracts over the underlying IdP. In practice:

| Sign-up path             | `email_verified` at first login | Why                                                                                                                                                  |
| ------------------------ | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Google                   | `true`                          | Google verifies all Gmail / Workspace addresses; the OIDC `email_verified` claim is essentially always `true`.                                       |
| Apple                    | `true`                          | Apple only returns emails it has validated, including `@privaterelay.appleid.com` aliases.                                                           |
| GitHub                   | `true`                          | WorkOS calls GitHub's `/user/emails`, picks the primary `verified: true` address, and refuses login if none exists.                                  |
| Microsoft / other social | `true`                          | Same pattern — the IdP guarantees ownership.                                                                                                         |
| WorkOS email + password  | `false` until verification step | WorkOS sends a verification email (currently a one-time code); the user must complete the verification step before `email_verified` flips to `true`. |

So the gate has the desired shape for free: blocks the email-password spam path, transparent for OAuth users.

## Proposed Solution

### 1. Persist `email_verified` on `User`

Add a boolean field to the custom user model, refreshed on every login. We persist rather than re-derive so that:

- The activity policy can read it via a single column lookup, no per-request call to the auth provider.
- The data is portable: if we switch providers, we keep the verification state on our side and re-confirm it from the new provider's claim on the next login.

```python
class User(AbstractUser):
    # ... existing fields from CustomUserModel.md ...
    email_verified = models.BooleanField(default=False)
```

The field belongs on `User`, not on a sidecar — see [CustomUserModel.md](CustomUserModel.md). `UserProfile` no longer exists.

Wire `email_verified` into the existing **mirrored-fields** refresh in `get_or_create_django_user()` ([backend/apps/accounts/api.py](../../../backend/apps/accounts/api.py)) — the same helper that already copies `email`, `first_name`, `last_name` from `auth_response.user` on every login. CustomUserModel.md step 7 explicitly flags `email_verified` as the next addition to that list. Add it to the helper and to the `update_fields=[...]` save call so it's refreshed on both create and returning-user paths. This keeps the local state in sync if a user verifies after their first sign-in, or if an admin un-verifies them upstream.

Note: `workos_user.email_verified` is already read live by the reactivation / first-time-link guards in the same function — that live read stays (it gates whether we bind a WorkOS account to a local row at all, which has to happen before the column would be trustworthy). Persisting the column is for downstream consumers, not for replacing those guards.

### 2. Expose `email_verified` to the activity policy

`email_verified` is read by the policy module described in [Authz.md](Authz.md). The launch-set activities (`catalog.edit`, `catalog.create`, `catalog.delete`, `claim.revert`) all include "email-verified" as a launch rule, so the policy is where the column is consumed.

Do **not** add `request.user.profile.email_verified` checks at individual write endpoints. The whole point of the Authz layer is that call sites ask `policy.check(user, "catalog.edit")` and don't know which inputs the policy considers. If you find yourself adding a second `email_verified` check next to an `is_authenticated` check, the call site should be going through the activity policy instead.

This is a server-side gate; the SPA may also hide edit affordances for unverified users for UX, but the backend is the source of truth.

### 3. UX for the email-password path

When an unverified user hits an activity-gated action, the policy denies with a stable code from the Authz denial-code registry (e.g. `verification_required`). The SPA's shared denial-handling UI maps that code to copy — "We sent a verification link to <email>. Click it, then refresh." — and offers a "resend verification email" button.

The resend button is the one piece of UX this doc owns: a new endpoint that calls `client.user_management.send_verification_email(user_id=...)`. The denial code, the copy, and the modal layout live with Authz, not here.

OAuth users never see any of this because their `email_verified` is already `true` at first login.

### 4. Migration / backfill

For existing local users (pre-feature):

- Default the new column to `False` at migration time.
- On their next login, `get_or_create_django_user()` will refresh from WorkOS and set the correct value.
- For users who don't log in soon: optionally, a one-shot management command that fetches each user's status from WorkOS via `client.user_management.get_user(user_id=...)` and backfills. Probably not worth writing unless we see a stuck cohort.

We don't need to lock down existing edits retroactively — this is a forward-looking spam gate, not a security retrofit.

### 5. Provider portability

The shape `email_verified: bool` is universal across OIDC providers — Clerk, Auth0, and self-hosted OIDC all expose the same claim. Switching providers means changing the right-hand side of `user.email_verified = <provider_user>.email_verified` in one function (the mirrored-fields refresh in `get_or_create_django_user`). Nothing else in the app needs to know how the bit was computed.

## Open questions

- **Do we let unverified users do anything beyond reading?** Probably yes — they can browse, follow, save favorites, etc. Only catalog-mutating actions should be gated.
- **Should we also gate account-linking flows?** Already done in [CustomUserModel.md](CustomUserModel.md): `get_or_create_django_user()` refuses to bind a WorkOS account to a local row (first-time link or reactivation) unless `inbound.email_verified` is true. No further work here.
- **Bot protection on the verification email itself?** Out of scope for this doc, but worth a follow-up if we see signups generating verification spam.

## Non-goals

- Reputation / trust scoring beyond the verified bit.
- Captcha / rate limiting (separate concerns; can layer on top later).
- Phone-number verification (no current product need).
- Mirroring 2FA / passkey state from the provider — those are auth-time concerns, enforced upstream.
