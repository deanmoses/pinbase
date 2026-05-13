# Usernames

The system uses WorkOS to handle authentication. Currently, when WorkOS hands us the user, we synthesize a username from their email address by stripping off the domain.

Instead, we want the user to choose their username. The username is their public identifier/handle, and as such:

- Exposing a portion of their email address without telling them is unacceptable.
- Exposing PII like 'john.smith' that may be in their email address without telling them is unacceptable
- They should be able to choose their public handle.

We landed on username because that's the best practice used by comparable user-generated content sites like Wikipedia.

## Invariants

- No username migration. We are pre-launch, know all the existing users, and they are cool with their existing usernames.
- Usernames must be URL-friendly. I think the existing logic for creating a username might have the right validation logic.

## How it works

### No User record until username is chosen

The user should not be a User in our system until they've chosen a username.

I want User.username to remain required, non-nullable and unique at the DB level like it is now. When WorkOS hands us a user, we don't create the User record until they've chosen their username.

This will require some rework, because currently the WorkOS callback immediately needs a Django User because it calls login(request, user, ...) after get_or_create_django_user(...). So holding off on creating the User record means adding a separate pending signup/onboarding state or something.

I see the following options:

- Pending Signup In Session
- PendingSignup Table

#### Session-based for now

The right approach for v1 is probably a short-lived pending signup object in the Django session.

The callback already depends on the same browser session for the WorkOS `state`
round-trip, and the user chooses their username immediately after the callback.
That makes the pending identity a continuation of one browser flow, not a durable
account-like object. Django is using server-side sessions, so this does not put
the pending email/name payload in a browser cookie.

The callback should split the current `get_or_create_django_user(...)` behavior
into two paths:

1. Existing local account matched by `workos_user_id`, verified email link, or
   reactivation: refresh mirrored WorkOS fields, call `login(...)`, and redirect
   to the original `next`.
2. No local account matched: store pending WorkOS identity in the session,
   redirect to the username onboarding page, and do **not** create or log in a
   `User`.

The pending session payload should include only what is needed to create the
eventual `User`. Something like:

```python
{
    "workos_user_id": workos_user.id,
    "email": workos_user.email,
    "email_verified": workos_user.email_verified,
    "first_name": workos_user.first_name or "",
    "last_name": workos_user.last_name or "",
    "next_url": next_url,
    "created_at": timezone.now().isoformat(),
}
```

Treat the payload as expired after a short window, e.g. 30 minutes. If it is
missing or expired, the user restarts sign-in. That is acceptable because no
local account exists yet.

##### Why not a `PendingSignup` table

A table is the right answer if pending signup becomes independently durable, such as:

- users can resume onboarding across browsers/devices (which would be cool)
- support needs to inspect pending attempts
- we need cleanup metrics
- we need to coordinate multiple pending attempts per WorkOS identity across sessions
- the pending state starts carrying policy/audit significance

A table would add a second identity-like lifecycle containing PII, cleanup semantics, uniqueness rules, and support states, so let's avoid it until we're sure we need it.

### Choosing a username

As the user types a username, we check whether it's already taken without them having to click submit.

If it's taken, the user must choose another: no silent suffixing for public handles, no automatic incrementing like myHandle1.

## Username policy

### Username format

Same URL shape as the current derived usernames, but make it explicit:

- lowercase ASCII letters, digits, and single hyphens
- no leading/trailing hyphen
- no '/', so we can use the username in routes
- **length**. Must stay within `User.username`'s 150-character column. Is there a reason to require something shorter? That's pretty long for a URL...
- collapse/normalization can be used for availability preview, but final submit must reject invalid input rather than silently changing the handle

### Reserved usernames

Reserve usernames that connote authority or would be confusing for other users to see: `admin`, `support`, `moderator`,`mod`, `staff`, `superuser`, `flipcommons`, flip-commons, `flip`, `the-flip`, theflip, flipcommons-team, flip-commons-team, flipcommons-admin, flipcommons-support, flipcommons-help, `museum`, the-museum, museum-support, museum-help, museum-staff, musuem-admin, help, official, team, m0derator, flipc0mmons, sysadmin, system, administrator, flipcommons-staff... TBD

Suffixes: -official, -team, -staff, -admin, -administrator, -help, -system... TBD

#### Variants of reserved usernames

Normalize before comparing to the reserved list — fold 0→o, 1→l, strip non-letters, lowercase — and reject if the normalized form hits a reserved entry.

#### Deferred reserved usernames

I would _like_ to reserve some of the following, but they need moderation/product policy, so let's defer them until later.

- Reserve manufacturer names for manufacturers.
- Reserve the names of the people credited with working on machines for those people.
- Trademarks, famous people, and impersonation?

Let's get the basic idea out for now.

#### Reserved list must be expandable w/o deploy - FOLLOW-UP

Reserved list needs to be expandable without a deploy. This is important but will be in a follow-up PR.

#### Admin can free up usernames - FOLLOW-UP

If we miss a username we need to reserve, we're stuck unless an admin can forcibly disable/rename. This is important but will be in a follow-up PR.

## Out of scope

- Allowing the user to change their username after the fact. Design it as if renames will exist later, but we're not implementing it right now.
- Any sort of secondary display name. Username will be all there is right now. We might have this in the future, but not now.
- A way to edit their first and last name, or mark them as public. WorkOS returns them and we store them, but we treat them as private right now. We will probably do this the future, but not in this PR.
- A user account page where the user can manager their information. We'll have that, but not in this PR.

## Code pointers

A WorkOS callback creates a local user via User.objects.create*user(...) without passing username in backend/apps/accounts/api.py (line 266). The manager then fills username from derive_unique_username(email) in backend/apps/accounts/models.py (line 76). derive_username() takes the email local-part before @, lowercases it, replaces ./*/+ with -, strips other chars, and uses that as the public username in backend/apps/accounts/models.py (line 15). The test explicitly verifies Alice.Smith+tag@example.com becomes alice-smith-tag in backend/apps/accounts/tests/test_models.py (line 19).
