"""Auth & user API endpoints."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import ClassVar, TypedDict

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Model
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from ninja import Router, Schema
from pydantic import Field

from apps.core.authz import (
    Activity,
    compute_capability_map,
    compute_row_capabilities,
    policy_user,
)
from apps.core.authz.markers import public_mutation
from apps.core.rate_limits import (
    RateLimitSpec,
    check_and_record_ip,
    check_and_record_session,
)
from apps.core.schemas import EntityLinkSchema, ErrorDetailSchema, RateLimitErrorSchema
from apps.core.types import EntityKey
from apps.provenance.entity_resolution import batch_resolve_entities
from apps.provenance.models import ChangeSet, Claim

from .auth_errors import (
    PendingInvalidError,
    UsernameRejectedError,
    UsernameTakenError,
)
from .models import User
from .pending import (
    PendingPayload,
    WorkOSUser,
    clear_pending,
    extract_workos_session_id,
    get_pending,
    put_pending,
)
from .reserved import is_reserved
from .schemas import (
    PendingInvalidErrorSchema,
    SignupCancelResponseSchema,
    SignupCheckResponseSchema,
    SignupPendingResponseSchema,
    SignupSubmitRequestSchema,
    SignupSubmitResponseSchema,
    UsernameRejectedErrorSchema,
    UsernameTakenErrorSchema,
)
from .usernames import UsernameFormatRejectReason, validate_username_format
from .workos_client import get_workos_client

log = logging.getLogger(__name__)

auth_router = Router(tags=["auth", "private"])
signup_router = Router(tags=["auth", "private"])
user_page_router = Router(tags=["private"])


# Rate-limit specs are built per-request from settings, NOT cached at
# module-load. That preserves the design intent ("tunable without code
# change") — overriding `settings.SIGNUP_*_RATELIMIT_*` at runtime
# (env, pytest's `settings` fixture, future constance) takes effect on
# the next request without a process restart. Spec construction is a
# frozen-dataclass with three fields; the cost is negligible.
def _spec(bucket: str, setting_key: str) -> RateLimitSpec:
    limit, window = getattr(settings, setting_key)
    return RateLimitSpec(bucket, limit, window)


# ── Schemas ──────────────────────────────────────────────────────────


class AuthStatusSchema(Schema):
    is_authenticated: bool
    id: int | None = None
    username: str | None = None
    first_name: str = ""
    last_name: str = ""
    # Verdict for every target-less registered activity. Anonymous
    # callers get an all-false map (every rule's first predicate is
    # `is_authenticated`). Target-aware activities (e.g. `claim.revert`)
    # are excluded; those verdicts come from per-resource hints embedded
    # in the resource's serializer.
    capabilities: dict[Activity, bool] = Field(default_factory=dict)


class EntityContributionSchema(Schema):
    entity: EntityLinkSchema
    edit_count: int
    last_edited_at: str


class UserChangeSetSchema(Schema):
    id: int
    note: str
    created_at: str
    entity: EntityLinkSchema
    capabilities: dict[Activity, bool] = Field(default_factory=dict)

    policy_activities: ClassVar[tuple[Activity, ...]] = (Activity.CHANGESET_UNDO,)
    policy_target_model: ClassVar[type[Model]] = ChangeSet


class UserProfileSchema(Schema):
    username: str
    member_since: str
    edit_count: int
    entities_edited: list[EntityContributionSchema]
    recent_edits: list[UserChangeSetSchema]


class EntityContributionRow(TypedDict):
    content_type_id: int
    object_id: int
    edit_count: int
    last_edited_at: datetime


# ── Helpers ──────────────────────────────────────────────────────────


class LoginRefusedError(Exception):
    """Raised when an inbound WorkOS login may not be honored.

    Surfaced as a 4xx in auth_callback. Reasons include: account is inactive
    and reactivation guards failed (e.g. unverified inbound email), or two
    WorkOS accounts trying to claim the same local row.
    """


def _refresh_mirrored_fields(user: User, workos_user: WorkOSUser) -> list[str]:
    """Copy WorkOS-side identity fields onto the local row. Returns dirty fields.

    Raises LoginRefusedError if the inbound email is already taken by another
    local row (case-insensitively) — that's two WorkOS accounts trying to
    converge onto one local email, which needs admin resolution rather than a
    DB-level IntegrityError surfacing as a 500.
    """
    dirty: list[str] = []
    new_email = workos_user.email
    if user.email != new_email:
        if (
            new_email.lower() != user.email.lower()
            and User.objects.filter(email__iexact=new_email)
            .exclude(pk=user.pk)
            .exists()
        ):
            _refuse_active_email_collision(user, workos_user)
        user.email = new_email
        dirty.append("email")
    new_first = workos_user.first_name or ""
    if user.first_name != new_first:
        user.first_name = new_first
        dirty.append("first_name")
    new_last = workos_user.last_name or ""
    if user.last_name != new_last:
        user.last_name = new_last
        dirty.append("last_name")
    new_email_verified = workos_user.email_verified
    if user.email_verified != new_email_verified:
        user.email_verified = new_email_verified
        dirty.append("email_verified")
    return dirty


def _refuse_active_email_collision(user: User, workos_user: WorkOSUser) -> None:
    log.error(
        "two WorkOS accounts claim same local user, refusing login until "
        "admin resolves: email=%s existing_workos_id=%s inbound_workos_id=%s",
        workos_user.email,
        user.workos_user_id,
        workos_user.id,
    )
    raise LoginRefusedError("Account conflict; contact an administrator.")


def _try_match_existing(workos_user: WorkOSUser) -> User | None:
    """Run the lookup branches. Returns a matched user, or None to mean 'create'.

    Raises LoginRefusedError for the refuse cases.
    """
    # Branch 1/2 — id lookup.
    try:
        user = User.objects.get(workos_user_id=workos_user.id)
    except User.DoesNotExist:
        pass
    else:
        if not user.is_active:
            # Soft-deleted users have workos_user_id cleared by the webhook,
            # so this is theoretically unreachable — log if it ever fires.
            log.error(
                "active workos_user_id hit on inactive row: user_id=%s workos_id=%s",
                user.pk,
                workos_user.id,
            )
            raise LoginRefusedError("Account is disabled.")
        dirty = _refresh_mirrored_fields(user, workos_user)
        if dirty:
            user.save(update_fields=dirty)
        return user

    # Branch 3/4 — email lookup.
    email_match = User.objects.filter(email__iexact=workos_user.email).first()
    if email_match is None:
        return None
    user = email_match
    if user.is_active:
        if user.workos_user_id is None:
            # First-time link: a local row exists with no provider binding
            # yet. Verified inbound email is required so an attacker can't
            # claim the row by signing up with the same email at the IdP
            # before the real owner does.
            #
            # Privileged rows (is_staff / is_superuser) are NEVER auto-linked
            # — the blast radius of a typo'd or expired bootstrap email is too
            # large. Operators grant admin access deliberately: sign in via
            # WorkOS as a regular user first, then tick is_staff/is_superuser
            # on that row in Django admin.
            if user.is_staff or user.is_superuser:
                log.error(
                    "refusing auto-link of privileged row: user_id=%s email=%s "
                    "inbound_workos_id=%s",
                    user.pk,
                    workos_user.email,
                    workos_user.id,
                )
                raise LoginRefusedError("Account conflict; contact an administrator.")
            if not workos_user.email_verified:
                raise LoginRefusedError(
                    "Please verify your email with the identity provider before signing in."
                )
            user.workos_user_id = workos_user.id
            dirty = ["workos_user_id", *_refresh_mirrored_fields(user, workos_user)]
            user.save(update_fields=dirty)
            return user
        # Active row already bound to a *different* workos_user_id — two
        # WorkOS accounts claim the same local user; admin must resolve.
        _refuse_active_email_collision(user, workos_user)
    if not workos_user.email_verified:
        raise LoginRefusedError(
            "Please verify your email with the identity provider before signing in."
        )
    # Reactivate.
    user.is_active = True
    user.workos_user_id = workos_user.id
    dirty = [
        "is_active",
        "workos_user_id",
        *_refresh_mirrored_fields(user, workos_user),
    ]
    user.save(update_fields=dirty)
    return user


def _require_pending(request: HttpRequest) -> PendingPayload:
    """Return the pending payload, or raise `PendingInvalidError` (401).

    **New pre-auth endpoints MUST call this before any rate-limit call or
    other code that writes the session.** The ordering is load-bearing
    (see below).

    Deliberately does NOT call `ensure_session_key`. A valid pending payload
    implies the callback already wrote a session row (that's where
    `put_pending` calls `ensure_session_key`), so on the success path the
    session_key is non-None. On the failure path, raising before any
    session write means anonymous probes to /pending, /check, /submit do
    NOT create a `django_session` row — closing the session-flood vector
    a pre-auth `ensure_session_key()` would have opened.

    The downstream rate-limiter assert (`session_key is not None`) still
    holds because rate-limiting only runs after this guard succeeds.
    """
    payload = get_pending(request)
    if payload is None:
        raise PendingInvalidError()
    return payload


# ── Endpoints ────────────────────────────────────────────────────────


@auth_router.get("/me/", response=AuthStatusSchema)
def auth_me(request: HttpRequest) -> AuthStatusSchema:
    """Return current session's authentication state.

    Always succeeds (no auth required). Returns is_authenticated=False for
    anonymous users.
    """
    user = request.user
    if isinstance(user, User):
        return AuthStatusSchema(
            is_authenticated=True,
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            capabilities=compute_capability_map(policy_user(user)),
        )
    assert isinstance(user, AnonymousUser)
    return AuthStatusSchema(
        is_authenticated=False,
        capabilities=compute_capability_map(policy_user(user)),
    )


@auth_router.get("/login/", url_name="workos_login", include_in_schema=False)
def auth_login(request: HttpRequest) -> HttpResponse:
    """Redirect to WorkOS AuthKit hosted login UI."""
    if not settings.WORKOS_API_KEY or not settings.WORKOS_CLIENT_ID:
        return HttpResponse(
            "WorkOS is not configured. Set WORKOS_API_KEY and WORKOS_CLIENT_ID.",
            status=503,
        )

    next_url = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        next_url = "/"

    state = secrets.token_urlsafe(32)
    request.session[f"auth_{state}"] = next_url

    try:
        client = get_workos_client()
        authorization_url = client.user_management.get_authorization_url(
            provider="authkit",
            redirect_uri=settings.WORKOS_REDIRECT_URI,
            state=state,
        )
    except Exception:
        log.exception("Failed to generate WorkOS authorization URL")
        return HttpResponse(
            "Sign-in is temporarily unavailable. Please try again later.",
            status=503,
        )
    return HttpResponseRedirect(authorization_url)


@auth_router.get("/callback/", url_name="workos_callback", include_in_schema=False)
def auth_callback(request: HttpRequest) -> HttpResponse:
    """Handle the OAuth callback from WorkOS."""
    code = request.GET.get("code")
    state = request.GET.get("state")
    if not code or not state:
        return HttpResponseBadRequest("Missing code or state parameter.")

    next_url = request.session.pop(f"auth_{state}", None)
    if next_url is None:
        return HttpResponseBadRequest("Invalid or expired state parameter.")

    try:
        client = get_workos_client()
        auth_response = client.user_management.authenticate_with_code(
            code=code,
        )
    except Exception:
        log.exception("WorkOS code exchange failed")
        return HttpResponseBadRequest(
            "Authentication failed. The login link may have expired — please try again."
        )

    try:
        user = _try_match_existing(auth_response.user)
    except LoginRefusedError as exc:
        log.warning("Login refused: %s", exc)
        return HttpResponseBadRequest(str(exc))
    if user is not None:
        login(request, user, backend="apps.accounts.backends.WorkOSBackend")
        return HttpResponseRedirect(next_url)

    # Brand-new user — stash WorkOS identity in the session and redirect
    # to onboarding so they can pick a handle. No User INSERT happens here,
    # so the retry-on-IntegrityError loop the old callback wore is gone;
    # the submit endpoint inherits the workos_user_id and username races.
    put_pending(
        request,
        auth_response.user,
        next_url,
        workos_session_id=extract_workos_session_id(auth_response.access_token),
    )
    return HttpResponseRedirect("/signup")


@auth_router.post("/logout/", response=AuthStatusSchema)
@public_mutation(
    "Session teardown — caller may already be partially logged out; "
    "no editorial action is being authorized."
)
def auth_logout(request: HttpRequest) -> AuthStatusSchema:
    """End the current session."""
    logout(request)
    # `request.user` is `AnonymousUser` after `logout()`. Populate the
    # capability map explicitly so the response shape matches `/me/`'s
    # anonymous branch — both bodies represent the same state.
    return AuthStatusSchema(
        is_authenticated=False,
        capabilities=compute_capability_map(policy_user(request.user)),
    )


# ── Signup (onboarding) ──────────────────────────────────────────────


def _format_reject_reason(username: str) -> UsernameFormatRejectReason | None:
    """Return the format reject reason, or None when valid.

    The validator carries a `code` matching `UsernameFormatRejectReason`
    on every raise. Missing code = bug in the validator, not a wire-format
    degradation, so fail loud rather than masking with a fake "bad_charset".

    Callers that want to surface the reason as an error (the submit
    endpoint) raise `UsernameRejectedError(reason=...)` on a non-None return.
    The availability check uses the reason directly in its 200 body.
    """
    try:
        validate_username_format(username)
    except ValidationError as exc:
        # PT017 is a pytest-only lint rule about test structure;
        # the assert is correct here in app code.
        assert exc.code is not None, (  # noqa: PT017
            "validate_username_format raised without code"
        )
        reason: UsernameFormatRejectReason = exc.code  # type: ignore[assignment]
        return reason
    return None


@signup_router.get(
    "/pending/",
    response={200: SignupPendingResponseSchema, 401: PendingInvalidErrorSchema},
)
def signup_pending(request: HttpRequest) -> SignupPendingResponseSchema:
    """Return identity fields for the onboarding-page header.

    Source is the pending session payload; missing/expired raises
    `PendingInvalidError` (401).
    """
    pending = _require_pending(request)
    return SignupPendingResponseSchema(
        first_name=pending["first_name"],
        last_name=pending["last_name"],
        email=pending["email"],
    )


@signup_router.get(
    "/check/",
    response={
        200: SignupCheckResponseSchema,
        401: PendingInvalidErrorSchema,
        429: RateLimitErrorSchema,
    },
)
def signup_check(request: HttpRequest, username: str) -> SignupCheckResponseSchema:
    """Availability check for a candidate username.

    Always 200 (when session is valid). Every outcome — format-invalid,
    reserved, taken, available — is a normal answer to "can the user
    use this handle?" The typed `reason` carries the discriminator;
    callers don't have to branch on status code.

    Order is `pending guard → rate limit` (see plan §Decisions locked).
    The pending guard short-circuits attackers without a legitimate
    session shape so their requests don't consume rate-limit slots; for
    real users whose session just expired, the typed `pending_invalid`
    is more informative than a 429.
    """
    _require_pending(request)
    check_and_record_session(
        request, _spec("signup_check_session", "SIGNUP_CHECK_RATELIMIT_SESSION")
    )
    check_and_record_ip(request, _spec("signup_check_ip", "SIGNUP_CHECK_RATELIMIT_IP"))

    reason = _format_reject_reason(username)
    if reason is not None:
        return SignupCheckResponseSchema(available=False, reason=reason)
    if is_reserved(username):
        return SignupCheckResponseSchema(available=False, reason="reserved")
    if User.objects.filter(username=username).exists():
        return SignupCheckResponseSchema(available=False, reason="taken")
    return SignupCheckResponseSchema(available=True, reason=None)


@signup_router.post(
    "/",
    response={
        200: SignupSubmitResponseSchema,
        400: UsernameRejectedErrorSchema,
        401: PendingInvalidErrorSchema,
        409: UsernameTakenErrorSchema,
        429: RateLimitErrorSchema,
    },
)
@public_mutation(
    "Pre-auth signup; gated by pending session payload, not @requires() "
    "because no User exists yet."
)
def signup_submit(
    request: HttpRequest, payload: SignupSubmitRequestSchema
) -> SignupSubmitResponseSchema:
    """Create the User row from pending payload + chosen username, then log in.

    Two races handled inline (callback no longer issues a User INSERT):
    - `workos_user_id` race (two tabs of the same signup): re-query the
      winner by `workos_user_id` and log the loser's session in as the
      winner. The loser's typed handle is silently dropped — acceptable
      per Usernames.md §Race. Logging in on the loser side (rather than
      returning 409 and trusting the winner's cookie) is deterministic:
      Django's `login()` rotates `session_key` via `cycle_key()`, so the
      losing tab's in-flight submit may not pick up the rotated cookie
      depending on response ordering.
    - `username` race (two users picking the same handle simultaneously):
      raises `UsernameTakenError` (409); pending payload stays intact so
      the user can pick again.
    """
    pending = _require_pending(request)
    check_and_record_session(
        request, _spec("signup_submit_session", "SIGNUP_SUBMIT_RATELIMIT_SESSION")
    )
    check_and_record_ip(
        request, _spec("signup_submit_ip", "SIGNUP_SUBMIT_RATELIMIT_IP")
    )

    username = payload.username
    if (reason := _format_reject_reason(username)) is not None:
        raise UsernameRejectedError(reason=reason) from None
    if is_reserved(username):
        raise UsernameRejectedError(reason="reserved")

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=pending["email"],
                username=username,
                first_name=pending["first_name"],
                last_name=pending["last_name"],
                workos_user_id=pending["workos_user_id"],
                email_verified=pending["email_verified"],
            )
    except IntegrityError:
        # Disambiguate by re-query, not by inspecting the exception:
        # psycopg's diag.constraint_name attribute isn't portable across
        # backends and SQLite tests would need a parallel code path.
        winner = User.objects.filter(workos_user_id=pending["workos_user_id"]).first()
        if winner is not None:
            # Sibling tab won the workos_user_id race. The winner was just
            # created from the same pending payload (same WorkOS callback,
            # same session), so first_name / last_name / email_verified
            # already match — do NOT call _refresh_mirrored_fields here.
            clear_pending(request)
            login(request, winner, backend="apps.accounts.backends.WorkOSBackend")
            return SignupSubmitResponseSchema(redirect_url=pending["next_url"])
        # Username collision against a different account.
        # `from None`: the IntegrityError is implementation detail; chaining
        # it onto the wire-shaped exception would leak the constraint
        # message into logs without informing the response. Same rationale
        # at the earlier UsernameRejectedError raise.
        raise UsernameTakenError() from None

    clear_pending(request)
    login(request, user, backend="apps.accounts.backends.WorkOSBackend")
    return SignupSubmitResponseSchema(redirect_url=pending["next_url"])


def _absolute_return_to(request: HttpRequest, path: str) -> str:
    """Resolve a relative return URL to absolute, since WorkOS requires that.

    The setting accepts either form so dev/test can use a bare path.
    """
    if path.startswith(("http://", "https://")):
        return path
    return request.build_absolute_uri(path)


@signup_router.post(
    "/cancel/",
    response={200: SignupCancelResponseSchema, 429: RateLimitErrorSchema},
)
@public_mutation(
    "Pre-auth signup cancel — clears pending state and returns the WorkOS "
    "logout URL. Idempotent; no editorial action is being authorized."
)
def signup_cancel(request: HttpRequest) -> SignupCancelResponseSchema:
    """Clear pending state and return a WorkOS logout URL.

    Idempotent — missing pending still returns a valid logout URL because
    the user's intent is "get me out." Rate-limited by IP only; a
    session-key limit would force a carve-out around ensure_session_key
    and only catch the absurd "user click-spams Not-you?" case.
    """
    check_and_record_ip(
        request, _spec("signup_cancel_ip", "SIGNUP_CANCEL_RATELIMIT_IP")
    )
    payload = get_pending(request)
    clear_pending(request)

    return_to = settings.SIGNUP_CANCEL_RETURN_URL
    if (
        payload is not None
        and payload["workos_session_id"]
        and settings.WORKOS_API_KEY
        and settings.WORKOS_CLIENT_ID
    ):
        try:
            client = get_workos_client()
            logout_url = client.user_management.get_logout_url(
                session_id=payload["workos_session_id"],
                return_to=_absolute_return_to(request, return_to),
            )
            return SignupCancelResponseSchema(logout_url=logout_url)
        except Exception:
            log.exception("Failed to build WorkOS logout URL; falling back")
    return SignupCancelResponseSchema(logout_url=return_to)


# ── User profile page ────────────────────────────────────────────────


@user_page_router.get(
    "/{username}/", response={200: UserProfileSchema, 404: ErrorDetailSchema}
)
def user_profile_page(request: HttpRequest, username: str) -> UserProfileSchema:
    """Page model for the user profile page: contribution history."""
    caller = policy_user(request.user)
    user = get_object_or_404(User, username=username)

    edit_count = ChangeSet.objects.filter(user=user).count()
    member_since = user.date_joined.isoformat()

    raw_entity_rows = list(
        Claim.objects.filter(user=user, changeset__isnull=False)
        .values("content_type_id", "object_id")
        .annotate(
            edit_count=Count("changeset", distinct=True),
            last_edited_at=Max("changeset__created_at"),
        )
        .order_by("-last_edited_at")
    )

    entity_rows: list[EntityContributionRow] = []
    for row in raw_entity_rows:
        last_edited_at = row["last_edited_at"]
        assert isinstance(last_edited_at, datetime)
        entity_rows.append(
            {
                "content_type_id": int(row["content_type_id"]),
                "object_id": int(row["object_id"]),
                "edit_count": int(row["edit_count"]),
                "last_edited_at": last_edited_at,
            }
        )

    resolved = batch_resolve_entities(
        [EntityKey(row["content_type_id"], row["object_id"]) for row in entity_rows]
    )

    entities_edited: list[EntityContributionSchema] = []
    for entity_row in entity_rows:
        meta = resolved.get(
            EntityKey(entity_row["content_type_id"], entity_row["object_id"])
        )
        if not meta:
            continue
        entities_edited.append(
            EntityContributionSchema(
                entity=meta,
                edit_count=entity_row["edit_count"],
                last_edited_at=entity_row["last_edited_at"].isoformat(),
            )
        )

    recent_changesets = (
        ChangeSet.objects.filter(user=user)
        .prefetch_related("claims")
        .order_by("-created_at")[:50]
    )

    cs_entity_keys: list[EntityKey] = []
    cs_first_claim: dict[int, EntityKey] = {}
    for cs in recent_changesets:
        prefetched_claims = cs.claims.all()
        if prefetched_claims:
            c = prefetched_claims[0]
            assert cs.pk is not None
            key = EntityKey(c.content_type_id, c.object_id)
            cs_first_claim[cs.pk] = key
            cs_entity_keys.append(key)

    cs_resolved = batch_resolve_entities(cs_entity_keys)

    recent_edits: list[UserChangeSetSchema] = []
    for cs in recent_changesets:
        assert cs.pk is not None
        ref = cs_first_claim.get(cs.pk)
        if not ref:
            continue
        meta = cs_resolved.get(ref)
        if not meta:
            continue
        recent_edits.append(
            UserChangeSetSchema(
                id=cs.pk,
                note=cs.note,
                created_at=cs.created_at.isoformat(),
                entity=meta,
                capabilities=compute_row_capabilities(
                    caller, cs, UserChangeSetSchema.policy_activities
                ),
            )
        )

    return UserProfileSchema(
        username=user.username,
        member_since=member_since,
        edit_count=edit_count,
        entities_edited=entities_edited,
        recent_edits=recent_edits,
    )


routers = [
    ("/auth/", auth_router),
    ("/auth/signup/", signup_router),
    ("/pages/user/", user_page_router),
]
