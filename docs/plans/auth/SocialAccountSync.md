# Social Account Sync

This document proposes capturing each user's underlying OAuth identities (Google `sub`, Apple `sub`, etc.) on every login into a local `accounts.SocialAccount` table.

## Status — deferred

Deferred; revisit when one of the problems below becomes urgent.

## Problem

**Reactivation safety.** The custom-user-model reactivation flow gates on `email_verified` and `banned_at IS NULL`, but doesn't catch the corporate-email-reassignment case (Alice leaves the company, Bob inherits `alice@oldcompany.com`, Bob signs in via the company SSO and could in principle claim Alice's history). A stable per-provider identifier on file would let us refuse the reactivation when the inbound `sub` doesn't match the prior one.

**Account-linking UX.** Supporting account-merge or explicit "link another provider" surfaces — or surfacing the error "this Google account is already linked to another user" — needs durable identity rows to compare against.

## NOT a problem

**Auth provider switching.** A migration from WorkOS to another auth provider or self-hosting would _appear_ to be reason to want this data already in our DB, but it isn't a real driver: at switch time we can call WorkOS's `/users/{id}/identities` once per user as part of the cutover and import the `(provider, sub)` pairs in bulk. The data we'd accumulate by capturing on every login is the same data we'd download from WorkOS during a planned migration — there's no information we can only get _now_. Capture-on-login would be insurance against an emergency switch where WorkOS's API is also down, which is narrow enough not to justify the ongoing complexity.

## Prerequisites and project invariants

**BYO OAuth credentials for every social provider — no exceptions.** We register the OAuth client at Google / Apple / GitHub / Microsoft ourselves and hand the `client_id`/`secret` to WorkOS, rather than using WorkOS's default credentials. This is the load-bearing detail that makes `SocialAccount` worth populating: with our own client, the `sub` Google returns is scoped to _our_ OAuth app, not WorkOS's. When we eventually plug those same credentials into a different managed provider (or self-host), Google issues the _same_ `sub` for the same human, so our stored `(google, sub)` pairs match and the new provider can pre-link without forcing re-login.

If we ever switched to WorkOS-owned credentials (or used them for a new provider), the `sub` values we'd accumulate would be scoped to WorkOS's client and useless after a switch — silently undermining the migration story. So this isn't a one-time setup detail, it's a permanent project invariant: when adding any new social provider, register the OAuth app under our own account first.

Currently confirmed BYO: **Google** (registered under our Google Cloud project, configured in WorkOS).

## Spike findings

**Underlying OAuth `sub` — not on the auth response; a separate API call is required.** Verified against the installed `workos` Python SDK: `AuthKitAuthenticationResponse` (returned by `authenticate_with_code`) carries `access_token`, `refresh_token`, `authentication_method`, `user`, `oauth_tokens`, etc. — no `sub` and no `identities`. The `User` object has no provider-issued identifier either; its `external_id` field is merchant-set, not provider-set. `OAuthTokens` carries the provider's access/refresh tokens but not the `sub`.

The `sub` is exposed only via `GET https://api.workos.com/user_management/users/{id}/identities`, which returns a JSON array of `{idp_id, type, provider}` objects. `idp_id` is documented as "the unique ID of the user in the external identity provider" — that's the OAuth `sub`. `provider` follows the same `GoogleOAuth` / `AppleOAuth` / `MicrosoftOAuth` naming the SDK already uses on `AuthenticationMethod`.

**SDK gap.** The Python SDK has no typed wrapper for this endpoint (no `client.user_management.list_user_identities()`). Add a thin helper in `apps/accounts/workos_client.py` that calls the endpoint via `httpx` with `Authorization: Bearer ${WORKOS_API_KEY}` and returns a `list[Identity]` (a local TypedDict mirroring `{idp_id, type, provider}`). Don't reach through the SDK's underscored `_http_client` — that's a private surface that can change between SDK versions.

**Cache strategy — per-provider, not per-user.** Only call on a user's first login via each provider. In `get_or_create_django_user`, map `auth_response.authentication_method` (`GoogleOAuth`, `AppleOAuth`, …) to a provider key (`google`, `apple`, …) and check `user.social_accounts.filter(provider=provider).exists()`. If false, fetch identities and upsert all returned rows — the endpoint returns every linked identity for the user, so a single call also backfills any providers linked outside our capture window. Email/password logins (`Password`, `Passkey`, `MagicAuth`) skip the call entirely.

## Proposed model

`accounts.SocialAccount` records each OAuth identity linked to a local user. The shape is just the natural OIDC mirror: provider id, the `sub` claim, when it was linked, when it was last used, and an allowlisted claims payload for forensics. Field names are chosen for clarity in our context, not to track any particular library.

```python
class SocialAccount(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )

    # OAuth provider id. "google", "apple", "github", "microsoft", etc.
    # No choices — the set grows as we enable providers.
    provider = models.CharField(max_length=64)

    # The OIDC `sub` claim from the underlying provider. Stable for a given
    # human-at-provider across managed-auth-provider switches.
    provider_sub = models.CharField(max_length=255)

    # When this identity was first linked to this user.
    linked_at = models.DateTimeField(auto_now_add=True)

    # When this identity was last used to sign in. Distinct from User.last_login
    # (which records any login, regardless of which identity was used).
    last_used_at = models.DateTimeField(auto_now=True)

    # Allowlisted OIDC claims we extracted from the inbound auth response.
    # Allowlist (not deny-list) so adding new keys is an explicit decision
    # rather than passively persisting whatever the provider chose to send.
    # Populated by the auth callback via OAUTH_PAYLOAD_ALLOWED_KEYS; the
    # save() override is a defense-in-depth strip in case a caller passes
    # a wider dict.
    oauth_payload = models.JSONField(default=dict)

    # Keys we intentionally keep from the inbound payload. Everything else
    # is dropped before persistence. Standard OIDC claims plus a couple of
    # forensic non-PII fields (issued-at, issuer).
    OAUTH_PAYLOAD_ALLOWED_KEYS = frozenset({
        "sub",
        "email",
        "email_verified",
        "name",
        "given_name",
        "family_name",
        "picture",
        "iat",
        "iss",
    })

    def save(self, *args, **kwargs):
        if isinstance(self.oauth_payload, dict):
            self.oauth_payload = {
                k: v for k, v in self.oauth_payload.items()
                if k in self.OAUTH_PAYLOAD_ALLOWED_KEYS
            }
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_sub"],
                name="accounts_socialaccount_unique_provider_sub",
            ),
            field_not_blank("provider"),
            field_not_blank("provider_sub"),
        ]
```

Notes:

- **OAuth users only.** Email/password sign-ups don't get a `SocialAccount` row — there's no underlying provider `sub`, only a WorkOS-side password hash. They're anchored to `User.workos_user_id` until we switch managed providers, at which point they need the password-reset path described in [ProviderSwitching.md](ProviderSwitching.md).
- **`(provider, provider_sub)` is globally unique.** A given Google account can be linked to at most one local user. Attempting to link an already-claimed Google account raises and the SPA shows "this account is already linked to another user."
- **CASCADE on `user`.** If a row is hard-deleted (a future GDPR purge command), its identities go too. Soft-delete (`is_active=False`) leaves the rows intact — they're needed for reactivation disambiguation.
- **Allowlist, not deny-list, in `save()`.** "Don't persist `access_token`/`refresh_token`/`id_token`" is the kind of rule that gets forgotten in a future code path, and id_token specifically embeds PII (email, name, picture URL) inside a JWT that anyone with DB read access can decode. Rather than a strip-list that has to grow when providers add claims, we keep an `OAUTH_PAYLOAD_ALLOWED_KEYS` allowlist of decoded claims we actually use. The `save()` override filters to that allowlist as defense in depth — even if a caller passes the raw inbound payload, only the allowed keys land in the column. Bypass paths (`bulk_create`, queryset `update`) exist but aren't in our planned write paths; the rule for any future caller is "go through `save()` or filter explicitly."

## Reactivation guard tightening

Once `SocialAccount` rows exist, extend the `get_or_create_django_user` reactivation predicate (defined in [CustomUserModel.md](CustomUserModel.md)) with a third clause:

**OAuth `sub` must match (when present).** If the user has any `SocialAccount` rows and the inbound login carries an OAuth `sub`, the inbound `(provider, sub)` must match one of them. A mismatch means "different human, don't reactivate" — this is the principled fix for the corporate-email-reassignment case. When the inbound login is email/password (no provider sub) and the user has only an email/password history (no `SocialAccount` rows), this check is a no-op.

The reactivation predicate becomes `is_active=False AND banned_at IS NULL AND inbound.email_verified=True AND (no sub mismatch with existing SocialAccount rows)`.

## Implementation steps

1. **Add the `SocialAccount` model** to `apps/accounts/models.py` with the constraints above.
2. **Add the WorkOS identities helper** at `apps/accounts/workos_client.py:fetch_user_identities(workos_user_id) -> list[Identity]` — `httpx` call, `Authorization: Bearer ${WORKOS_API_KEY}`, local TypedDict. Don't use the SDK's private `_http_client`.
3. **Wire the upsert into `get_or_create_django_user`.** For OAuth logins, derive the provider key from `auth_response.authentication_method`; if no `SocialAccount` row exists for `(user, provider)`, fetch identities and upsert every returned row.

   Use explicit get-or-create-with-conflict-detection — not `get_or_create`, not `update_or_create`. Both have hazards: `get_or_create` doesn't refresh the existing row, so `last_used_at` (auto_now) freezes at link-time and `oauth_payload` never reflects later claim changes. `update_or_create` would silently re-bind a row to a new user when the same `(provider, provider_sub)` pair exists under a different `user_id` — that's exactly the "different local user already claims this account" case we want to refuse loudly. So:

   ```python
   try:
       sa = SocialAccount.objects.get(provider=p, provider_sub=s)
   except SocialAccount.DoesNotExist:
       SocialAccount.objects.create(user=user, provider=p, provider_sub=s, oauth_payload=claims)
   else:
       if sa.user_id != user.id:
           raise SocialAccountConflict(...)  # different local user owns this Google/Apple/etc. account
       sa.oauth_payload = claims
       sa.save(update_fields=["oauth_payload", "last_used_at"])
   ```

   `last_used_at` _must_ appear in `update_fields` even though it's `auto_now=True` — when `update_fields` is specified, Django writes only the listed columns, and auto_now-on-save only takes effect for columns that will actually be written. Easy to miss; spell it out.

   `oauth_payload` is reassigned (not mutated in place) so `SocialAccount.save()`'s allowlist filter runs on the new payload, stripping any new bearer tokens or unrecognized claims the provider added since the row was created.

4. **Tighten the reactivation guard** with the `(provider, provider_sub)` mismatch check described above.
5. **Register `SocialAccount` with a read-only admin.** Rows are written by the auth flow at login, not by hand — read-only prevents an admin from accidentally creating a row that would let someone log in as another user.
6. **Backfill (optional).** For existing users, run a one-time management command that calls `fetch_user_identities` for each user with a `workos_user_id` and inserts their identities. Skip if launching this with no user base, or if WorkOS's identities API is the part we're trying to migrate away from (in that case backfill from the new provider instead).

## Coordination with other auth plans

- **[CustomUserModel.md](CustomUserModel.md)** — defines `User.workos_user_id` (managed-provider pointer) and the v1 reactivation guards (email_verified + banned_at). This doc adds the OAuth-layer identifiers that survive a managed-provider switch and tightens the reactivation guard.
- **[Verification.md](Verification.md)** — originally proposed an external-identity table; this is that table, deferred until needed.
- **[ProviderSwitching.md](ProviderSwitching.md)** — depends on this data when re-linking users post-switch. If we ship a switch before this lands, the playbook is "force re-link via email" instead of "pre-link by `(provider, sub)`."

## Non-goals

- **Account merge for the same human across two providers.** Future doc.
- **Backfilling for users who pre-date this feature, when WorkOS itself is the part we're migrating off.** A switch-time backfill from the _new_ provider is cleaner.
