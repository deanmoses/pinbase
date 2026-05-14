# Usernames

The system uses WorkOS to handle authentication. Currently, when WorkOS hands us the user, we synthesize a username from their email address by stripping off the domain.

Instead, we want the user to choose their username. The username is their public identifier/handle, and as such:

- Exposing a portion of their email address without telling them is unacceptable.
- Exposing PII like 'john.smith' that may be in their email address without telling them is unacceptable
- They should be able to choose their public username.

We landed on username because that's the best practice used by comparable user-generated content sites like Wikipedia.

## Invariants

- No username migration.
  - We are pre-launch, know all existing users, and they are cool with their existing usernames. We have run a script that their current usernames meet the validation requirements -- including length 20 -- in this doc. And if that changes, DB migration fails and we address it then.
- Usernames must be URL-friendly

## Username policy

### Username format

Same URL shape as the current derived usernames, but make it explicit:

- **allowed characters**
  - lowercase ASCII letters, digits, and single hyphens
    - Yes, this excludes users whose names use non-Latin scripts. We accept this tradeoff for URL safety
  - no leading/trailing hyphen
  - No underscore. No other special characters. In particular no '/', so we can use usernames in routes
- **min length**: 3 chars
- **max length**: 20 chars
  - Any longer and it causes problems for attribution chips, comment headers, and @mentions
  - 20 is what Reddit uses and they're doing all right
  - 30 is Instagram/Mastodon/Discord. We can relax later to here, but we can never tighten to 20.
- collapse/normalization can be used for availability preview, but final submit must reject invalid input rather than silently changing the username

### Reserved usernames that connote authority

Two lists, symmetric: each is reserved alone, and reserved in combination with any entry from the other list (either order).

Suffixes (alone and in front of stems): official, team, staff, admin, administrator, help, system, mod, moderator, sysadmin, superuser, support ... TBD

Stems (alone and in front of suffixes): flipcommons, flip-commons, flip, the-flip, theflip, museum, the-museum ... TBD

#### Matching rule

The goal is to block obvious impersonation while not over-blocking legitimate usernames that merely contain a reserved word as a substring.

A candidate is reserved when, ignoring presentation tricks, it spells out a reserved word or a reserved combination. "Presentation tricks" covers:

- **Case** — `Admin` and `admin` are the same username for this purpose.
- **Hyphens, underscores, and other punctuation** — `flip-commons` and `flipcommons` are the same.
- **Letter-shaped digit substitution (homoglyphs)** — `m0derator` reads as `moderator`; `flipc0mmons` reads as `flipcommons`.
- **Digit padding around a reserved word** — `admin99`, `flip2024`, `999admin`. A reserved word with extra digits at either end is still impersonation.

The match is on **equality** of the cleaned-up form, not substring. That keeps short stems like `flip` from blocking legitimate usernames like `flipperjones`, and short affixes like `mod` from blocking `modular`.

A candidate is also reserved if its cleaned-up form is a reserved stem joined with a reserved affix in either order (`flipadmin`, `adminflip`) — but not two affixes joined (`staffhelp` is allowed; that combination doesn't convey authority on its own).

Mixed attacks count too: `flipc0mmons1` is blocked (trailing-digit padding plus interior homoglyph both apply).

#### Deferred reserved usernames - FOLLOW-UP

I would _like_ to reserve some of the following, but they need moderation/product policy, so let's defer them until later.

- Reserve manufacturer names for manufacturers.
- Reserve the names of the people credited with working on machines for those people.
- Trademarks, famous people, and impersonation?
- Profanity / slurs

Let's get the basic idea out for now.

#### Reserved list must be expandable w/o deploy - FOLLOW-UP

Reserved list needs to be expandable without a deploy. This is important but will be in a follow-up PR.

#### Admin can free up usernames - FOLLOW-UP

If we miss a username we need to reserve, we're stuck unless an admin can forcibly disable/rename. This is important but will be in a follow-up PR.

## Treat username as mutable

V1 won't allow the user to change their username after the fact, but we probably will in the future. This means username is NOT a stable identifier and MUST NOT be treated as such. Meaning:

- **Database**. Any place we store a reference to a user in the database, store the user's db FK not their username.
- **Caches**. Caches must key by user ID. Including CDN caches.
- **API payloads**. API responses must include both user ID and username, so that the front end can use the stable ID as necessary.
- **Logs**. Log entries must write both user ID _and_ username.
- **@mentions**. If we support user @mentions, we turn those into IDs in the DB. We already have a wikilink system that serializes and deserializes public IDs like slugs into IDs in the DB.

When we do allow username changes in the future:

- prevent users from renaming again in N hours/days, to prevent spoofing
- probably redirect old user URLs to the new user URL, but that's TBD
- we want new users to be able to take the old username, but that requres careful design. TBD.

## Account deletion

For v1, username does NOT free up when a user deactivates.

## User creation from Django Admin/CLI

createsuperuser and any management commands must enforce same username policy with regards to uniqueness and allowed characters, but not reserved usernames — createsuperuser is operator-run, not user-facing, so reserved-list enforcement isn't a real risk there.

## Email verification

WorkOS verifies the user's email before even sending them our way. We don't re-check. We store email_verified from the pending payload for future reference, not a decision point.

## Out of scope

- Allowing the user to change their username after the fact. Design it as if renames will exist later, but we're not implementing it right now.
- Any sort of secondary display name. Username will be all there is right now. We might have this in the future, but not now.
- A way to edit their first and last name, or mark them as public. WorkOS returns them and we store them, but we treat them as private right now. We will probably do this the future, but not in this PR.
- A user account page where the user can manager their information. We'll have that, but not in this PR.

## Design

### Validation

- **Uniqueness** → existing DB unique constraint, already in place.
- **Length** → DB CHECK constraint (min/max), per the project's "validate in the database" convention.
- **Charset and hyphen rules** → **app-layer only**, because SQLite doesn't suport regex, and Django's per-connection `re`-backed registration doesn't extend to CHECK DDL. Instead, the format validator is wired as a Django field validator (so admin add-form, `createsuperuser`, and `full_clean()` paths run it) AND is invoked explicitly in the manager's `_create_user` (so every programmatic write path runs it — admin, factory, CLI, signup-submit). The manager is the chokepoint.
- **Reserved list** → invoked **only** from the user-facing signup submit endpoint, not from the manager. Putting it in `_create_user` would also block the admin/CLI path, which is exempt from reserved-list enforcement

### No User record until username is chosen

The user should not be a User record in our system until they've chosen a username.

User.username must remain required, non-nullable and unique at the DB level like it is now. When WorkOS hands us a user, we don't create the User record until they've chosen their username.

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

1. Existing local account matched. Three sub-paths, all converge on the same
   outcome — refresh mirrored WorkOS fields, call `login(...)`, redirect to
   the original `next`:
   - `workos_user_id` matches an active local user (the common case).
   - Email matches an active local user that predates WorkOS and has no
     `workos_user_id` yet: bind it on first link.
   - Email matches a soft-deleted local user: reactivate.
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

### Flow of choosing a username

As the user types a username, we check whether it's already taken without them having to click submit.

If it's taken, the user must choose another: no silent suffixing for public usernames, no automatic incrementing like myUsername1.

### Submitting the chosen username

When the user submits, the server does the following in a single transaction:

1. Load the pending payload from the session. If missing or expired, return an error that sends the user back to sign-in.
2. Validate the chosen username against the format rules and the reserved list.
3. Create the `User`, copying the mirrored fields (`workos_user_id`, email, first/last name, `email_verified`) from the pending payload.
4. Clear the pending payload from the session.
5. Call `login(request, user, ...)` and redirect to `next_url`.

#### Both signup endpoints are unauthenticated

The live availability-check endpoint and the submit endpoint both run before any `User` exists, so neither can sit behind the usual `@requires(Activity.X)` authz. Both are gated only by "valid, unexpired pending payload in this session."

#### Race: availability preview said "free", submit collides

The live check during typing is advisory. Between preview and submit, another user can claim the same username. At submit time the DB unique constraint will raise `IntegrityError`. We catch it and return a form-level error ("just taken, pick another") that re-renders the onboarding page with the pending payload intact. No 500, no lost pending state.

#### Race: double-submit or two-tab signup

The frontend disables the submit button on first click and re-enables only on error response. That handles the common case (impatient double-click) cleanly. The backend race handling below is the correctness backstop for the cases the frontend can't cover: two tabs (each with its own button state), client-side retry after a network hiccup, or a buggy/hostile client.

Two requests can still land near-simultaneously for the same `workos_user_id` — two tabs submitting different usernames, or a retry after a timeout. The `User.workos_user_id` unique constraint prevents duplicate accounts at the DB level. On the second request:

1. Detect the `IntegrityError` on `workos_user_id` (distinct from the username-collision case above).
2. Look up the existing `User` by `workos_user_id`, clear the pending payload, log them in, and redirect to `next_url`.
3. The username chosen in the losing request is discarded silently — the user is now logged in with the username chosen in the winning request, which is acceptable because they just chose it themselves seconds earlier.

### Case handling and lookups

The same rule applies at every backend input point — the live check endpoint, the submit endpoint, URL routing for `/users/<username>`, and any future rename flow:

- The editor lowercases as the user types so they don't fight the form. This is UX comfort only.
- The backend rejects any input containing uppercase — it does NOT silently lowercase. A curl/postman submit with `JohnDoe` is rejected, same principle as the format rules above (final submit must reject invalid input rather than silently change the username).
- Lookups are strict, not case-folded. `/users/JohnDoe` returns 404, not a 301 to `/users/johndoe`. The validation rule and the lookup rule are the same rule: if it's not a valid username, it doesn't exist.
