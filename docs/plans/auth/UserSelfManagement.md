# User Self-Management

## Problem

Today a Flipcommons user has no way to edit anything about themselves. Username is user-chosen at signup (see [Usernames.md](Usernames.md)), names come from whatever the auth provider sent, and there's no settings page at all. That's fine for an empty wiki; it stops being fine the first time someone wants:

- A different avatar than the one Google has of them.
- To stop receiving notification emails we haven't built yet but will.
- To delete their account (GDPR / personal preference).
- To rename their username (out of scope here — see [Usernames.md](Usernames.md) for the future rename design).

We need a settings page. The interesting design questions aren't _what_ goes on it — they're **which fields we own vs. defer to the auth provider**, and how we keep those two sides honest.

This doc proposes the split, the edit affordances, and the data model implications.

## Two layers, owned by different systems

The clean split:

- **Identity layer — owned by the auth provider.** Email, password, MFA, linked OAuth accounts, account closure at the auth level. The provider has hosted UI for all of this; we deep-link into it rather than rebuilding.
- **Site layer — owned by Flipcommons.** Bio, avatar choice, notification preferences, on-site account state. We host the form. (Username also lives here, but it's user-chosen at signup, not editable on the settings page in v1 — see [Usernames.md](Usernames.md). Username IS the public display identity; there's no separate display-name field.)

The settings page is a single Flipcommons-rendered surface that exposes both, with the identity-layer rows being links / buttons that hand off to the provider's user portal (`client.user_management.get_user_management_url(...)` for WorkOS; equivalent SDK methods for Clerk and Auth0). The user perceives a single "settings" experience; the architecture stays clean.

## Field-by-field proposal

| Field                                     | Owned by           | User can edit? | Notes                                                                                                                                                 |
| ----------------------------------------- | ------------------ | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Email                                     | Provider           | Yes (provider) | Deep-link to provider's hosted UI. Webhook syncs change back to us ([Webhooks.md](Webhooks.md)).                                                      |
| Password                                  | Provider           | Yes (provider) | Provider's UI. We never see it.                                                                                                                       |
| MFA / passkeys                            | Provider           | Yes (provider) | Provider's UI. We don't mirror state.                                                                                                                 |
| Linked OAuth accounts (Google, GitHub, …) | Provider           | Yes (provider) | Provider's UI. We mirror `(provider, sub)` pairs at login (see [EmailVerification.md](EmailVerification.md)).                                         |
| First / last name                         | Provider, mirrored | Yes (provider) | Synced from provider, treated as PII — never rendered publicly in v1. Future opt-in feature deferred (see [Usernames.md](Usernames.md) out-of-scope). |
| **Bio**                                   | Flipcommons        | Yes            | Short markdown blurb on the public profile page.                                                                                                      |
| **Avatar source**                         | Flipcommons        | Yes            | Choice: "use the picture from my auth provider" (default) or "upload one." Stored as an enum + optional uploaded file.                                |
| **Notification preferences**              | Flipcommons        | Yes            | Forward-looking — at minimum a master "email me about activity on entities I edited" toggle.                                                          |
| **Account deletion**                      | Provider           | Yes (provider) | User closes their account at the auth provider; the `user.deleted` webhook flips `is_active=False` on our side. See [Webhooks.md](Webhooks.md).       |
| Username (`User.username`)                | Flipcommons        | No (v1)        | User-chosen at signup. V1: no renames after signup — see [Usernames.md](Usernames.md) for the future rename design.                                   |

## Avatar — "use provider" vs. "upload"

The provider gives us a `profile_picture_url` ([EmailVerification.md](EmailVerification.md)). For most users that's fine. But a user who signed up with a corporate Google account may not want their work headshot on a hobby pinball wiki. Offer a choice:

```python
class UserProfile(TimeStampedModel):
    AvatarSource = models.TextChoices("AvatarSource", "PROVIDER UPLOADED INITIALS")
    avatar_source = CharField(choices=AvatarSource.choices, default="PROVIDER")
    avatar_uploaded = ImageField(null=True, blank=True)
```

Render order: if `avatar_source == "UPLOADED"` and the file exists, use it. If `"PROVIDER"` and we have a URL, use that. Otherwise generate an initials-based avatar deterministically from the username.

## Account deletion

A user wanting to leave closes their account at the auth provider. The settings page deep-links to the provider's account-closure UI; we don't call a delete API on their behalf, so consent is unambiguous and provider-side.

When the provider's `user.deleted` webhook arrives ([Webhooks.md](Webhooks.md)), we soft-delete on our side: `is_active=False`, `workos_user_id=None`, contribution history preserved with attribution. That's the only lifecycle state we track on our side — there's no separate self-service "deactivate but keep my account" mode. (Realistic intents — "stop emailing me," "hide my profile" — are covered by the notification and privacy toggles above.)

## What the settings page looks like

A single Flipcommons-rendered page at `/settings/`, organized into sections:

- **Profile** — bio, avatar source. (Username is shown read-only; rename is a future feature.)
- **Account** — email (read-only with "change at provider" link), connected logins (read-only with "manage at provider" link), password (button: "change password at provider").
- **Notifications** — toggles, currently only one or two.
- **Privacy** — show-real-name-on-edits toggle, "view my contribution history as the public sees it" link.
- **Danger zone** — delete account (deep-links to the provider's account-closure UI).

All non-trivial mutations go through the same claims-based write path described in [Provenance.md](../../Provenance.md) — bio changes are user-inputted catalog-_adjacent_ fields. _But_ they're metadata about the user, not about a catalog entity, so they probably aren't claims (claims are scoped to catalog entities). Worth a quick design check before implementation: do we want user-profile edits in the changeset audit log, or just on `UserProfile` directly with a simple `updated_at`? My instinct is the latter — user-profile edits aren't conflict-resolution-worthy data.

## Provider portability stays intact

Nothing here depends on Clerk's `username` field, or Auth0's profile UI shape, or WorkOS's hosted account portal specifically. Each provider has _some_ user-portal URL that we deep-link to; the URL is the only provider-specific value. The owned data (bio, avatar choice, notification prefs) lives on `User` and migrates with the user (see [ProviderSwitching.md](ProviderSwitching.md)).

## Open questions

- **Username rename redirects?** Covered in [Usernames.md](Usernames.md) — when renames ship, do we 301 old URLs to new? TBD.
- **Profanity / abuse on usernames?** Probably not worth a filter at our scale. Reactive moderation via setting `is_active=False` (see [CustomUserModel.md](CustomUserModel.md)).
- **Multiple connected logins?** Today our model assumes one provider. If we let Clerk users link Google + GitHub, we'd surface "connected accounts" with disconnect buttons — but the actual managing happens at the provider.
- **Should bio support markdown?** Yes, but a restricted dialect (no images, no embeds, no HTML). Same renderer we'll eventually use for change-set notes.

## Non-goals

- **Building our own password / MFA UI.** That's the provider's job; the whole point of the auth split is to not own this.
- **A full audit log of user-profile edits.** `updated_at` is enough; we're not in the user-profile-history business.
- **Cross-provider profile sync.** If a user has Clerk and another login, we don't reconcile fields between them — last write wins.
- **A separate display name.** Username IS the public display identity. First/last name are PII; we don't render them publicly in v1.
