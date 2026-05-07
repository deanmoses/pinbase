"""Auth & user API endpoints."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import Protocol, TypedDict

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.db.models import Count, Max
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from ninja import Router, Schema

from apps.core.schemas import ErrorDetailSchema
from apps.core.types import EntityKey
from apps.provenance.entity_resolution import batch_resolve_entities
from apps.provenance.models import ChangeSet, Claim

from .models import User
from .workos_client import get_workos_client

log = logging.getLogger(__name__)

auth_router = Router(tags=["auth", "private"])
user_page_router = Router(tags=["private"])


# ── Schemas ──────────────────────────────────────────────────────────


class AuthStatusSchema(Schema):
    is_authenticated: bool
    id: int | None = None
    username: str | None = None
    is_superuser: bool = False
    first_name: str = ""
    last_name: str = ""


class EntityContributionSchema(Schema):
    entity_href: str
    entity_name: str
    entity_type_label: str
    edit_count: int
    last_edited_at: str


class UserChangeSetSchema(Schema):
    id: int
    note: str
    created_at: str
    entity_href: str
    entity_name: str
    entity_type_label: str


class UserProfileSchema(Schema):
    username: str
    member_since: str
    edit_count: int
    entities_edited: list[EntityContributionSchema]
    recent_edits: list[UserChangeSetSchema]


class WorkOSUser(Protocol):
    id: str
    email: str
    email_verified: bool
    first_name: str | None
    last_name: str | None


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


_MIRRORED_FIELDS = ("email", "first_name", "last_name")


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


def get_or_create_django_user(workos_user: WorkOSUser) -> User:
    """Match or create a local User from an inbound WorkOS user payload.

    Branches:
      1. workos_user_id hit, active → refresh mirrored fields, return.
      2. workos_user_id hit, inactive → refuse (theoretically unreachable;
         the webhook clears workos_user_id on soft-delete).
      3a. Email hit, active, workos_user_id IS NULL, email_verified=True
          → first-time link (bind workos_user_id, refresh fields). Covers
          the bootstrap-superuser case (`make superuser` then sign in).
      3b. Email hit, active, workos_user_id already bound elsewhere
          → refuse (two WorkOS accounts claim same local user).
      4. Email hit, soft-deleted, email_verified=True → reactivate, return.
         Email hit, guards failed → refuse; never silently fork identity.
      5. No hit → create. On IntegrityError (concurrent first-login race
         on email, workos_user_id, or username), re-run the lookup branches
         and re-derive the username — the winning row is now visible — up
         to a small bound, then propagate.
    """
    last_exc: IntegrityError | None = None
    for _attempt in range(3):
        match = _try_match_existing(workos_user)
        if match is not None:
            return match
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=workos_user.email,
                    first_name=workos_user.first_name or "",
                    last_name=workos_user.last_name or "",
                    workos_user_id=workos_user.id,
                )
        except IntegrityError as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


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
            is_superuser=user.is_superuser,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    assert isinstance(user, AnonymousUser)
    return AuthStatusSchema(is_authenticated=False)


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
        user = get_or_create_django_user(auth_response.user)
    except LoginRefusedError as exc:
        log.warning("Login refused: %s", exc)
        return HttpResponseBadRequest(str(exc))
    login(request, user, backend="apps.accounts.backends.WorkOSBackend")
    return HttpResponseRedirect(next_url)


@auth_router.post("/logout/", response=AuthStatusSchema)
def auth_logout(request: HttpRequest) -> AuthStatusSchema:
    """End the current session."""
    logout(request)
    return AuthStatusSchema(is_authenticated=False)


@user_page_router.get(
    "/{username}/", response={200: UserProfileSchema, 404: ErrorDetailSchema}
)
def user_profile_page(request: HttpRequest, username: str) -> UserProfileSchema:
    """Page model for the user profile page: contribution history."""
    _ = request
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
                entity_href=meta["href"],
                entity_name=meta["name"],
                entity_type_label=meta["type_label"],
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
                entity_href=meta["href"],
                entity_name=meta["name"],
                entity_type_label=meta["type_label"],
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
    ("/pages/user/", user_page_router),
]
