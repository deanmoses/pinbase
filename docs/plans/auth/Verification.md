# Email Verification Gate for Edits

## Problem

Flipcommons is a public, user-editable wiki. Anyone who completes the sign-up flow today can immediately make catalog edits. That's a spam vector: an attacker can register with a throwaway email-password account and start writing claims before they've proved they own the email address. We have no signal in the request path that distinguishes a verified human from a bot that just clicked through sign-up.

To combat this, edits should require a verified email. Social sign-ins (Google, Apple, GitHub, Microsoft) already prove email ownership at the IdP, so legitimate OAuth users should pass the gate without seeing it. Only the email-password sign-up path — the path a spammer would actually use — should be slowed down by "click the link we sent you."

We want to do this without coupling our domain code to WorkOS internals. Whatever we store should survive a migration to a new auth provider (Clerk, Auth0, self-hosted OIDC) -- see [ProviderSwitching.md](ProviderSwitching.md).

## What `email_verified` actually means per provider

The WorkOS User object exposes a single `email_verified: bool` that abstracts over the underlying IdP. In practice:

| Sign-up path             | `email_verified` at first login | Why                                                                                                                 |
| ------------------------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Google                   | `true`                          | Google verifies all Gmail / Workspace addresses; the OIDC `email_verified` claim is essentially always `true`.      |
| Apple                    | `true`                          | Apple only returns emails it has validated, including `@privaterelay.appleid.com` aliases.                          |
| GitHub                   | `true`                          | WorkOS calls GitHub's `/user/emails`, picks the primary `verified: true` address, and refuses login if none exists. |
| Microsoft / other social | `true`                          | Same pattern — the IdP guarantees ownership.                                                                        |
| WorkOS email + password  | `false` until link clicked      | WorkOS sends a verification email; the user must click before `email_verified` flips to `true`.                     |

So the gate has the desired shape for free: blocks the email-password spam path, transparent for OAuth users.

## Proposed Solution

### 1. Persist `email_verified` on `UserProfile`

Add a boolean field, refreshed on every login. We persist rather than re-derive so that:

- Edits can be gated by a single column lookup, no per-request call to the auth provider.
- The data is portable: if we switch providers, we keep the verification state on our side and re-confirm it from the new provider's claim on the next login.

```python
class UserProfile(TimeStampedModel):
    user = OneToOneField(...)
    workos_user_id = CharField(...)
    priority = PositiveSmallIntegerField(...)
    email_verified = BooleanField(default=False)
```

Update `get_or_create_django_user()` (`backend/apps/accounts/api.py:111`) to write `profile.email_verified = workos_user.email_verified` on every login — both create and returning-user paths. This keeps the local state in sync if a user verifies after their first sign-in, or if an admin un-verifies them upstream.

### 2. Gate edits on `profile.email_verified`

A single check in the write path. The natural choke point is the same place `request.user.is_authenticated` is already checked for edit endpoints — add `request.user.profile.email_verified` alongside it. Unverified users get a clear error response that the SPA can render as "Please verify your email to start editing," with a link or button that triggers a re-send via WorkOS.

This is a server-side gate; the SPA may also hide edit affordances for unverified users for UX, but the backend is the source of truth.

### 3. UX for the email-password path

When an unverified user hits an edit action:

- API returns a structured error (e.g. `403` with a `code: "email_not_verified"` body) so the SPA can react.
- SPA shows a banner / modal: "We sent a verification link to <email>. Click it, then refresh."
- Provide a "resend verification email" button that calls a new endpoint, which in turn calls `client.user_management.send_verification_email(user_id=...)`.

OAuth users never see any of this because their `email_verified` is already `true` at first login.

### 4. Migration / backfill

For existing local users (pre-feature):

- Default the new column to `False` at migration time.
- On their next login, `get_or_create_django_user()` will refresh from WorkOS and set the correct value.
- For users who don't log in soon: optionally, a one-shot management command that fetches each user's status from WorkOS via `client.user_management.get_user(user_id=...)` and backfills. Probably not worth writing unless we see a stuck cohort.

We don't need to lock down existing edits retroactively — this is a forward-looking spam gate, not a security retrofit.

### 5. Provider portability

The shape `email_verified: bool` is universal across OIDC providers — Clerk, Auth0, and self-hosted OIDC all expose the same claim. Switching providers means changing the right-hand side of `profile.email_verified = <provider_user>.email_verified` in one function. Nothing else in the app needs to know how the bit was computed.

## Open questions

- **Do we let unverified users do anything beyond reading?** Probably yes — they can browse, follow, save favorites, etc. Only catalog-mutating actions should be gated.
- **Should we also gate account-linking flows?** A verified email is what makes the email-fallback branch in `get_or_create_django_user()` (api.py:129) safe; it's already checked there. Worth auditing to confirm that branch isn't ever reached with `email_verified=False`.
- **Bot protection on the verification email itself?** Out of scope for this doc, but worth a follow-up if we see signups generating verification spam.

## Non-goals

- Reputation / trust scoring beyond the verified bit.
- Captcha / rate limiting (separate concerns; can layer on top later).
- Phone-number verification (no current product need).
- Mirroring 2FA / passkey state from the provider — those are auth-time concerns, enforced upstream.
