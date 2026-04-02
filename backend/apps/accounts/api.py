"""Auth API endpoints: status, login (WorkOS redirect), callback, logout."""

from __future__ import annotations

import base64
import json
import logging
import secrets
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from ninja import Router, Schema

from .models import UserProfile
from .workos_client import get_workos_client

log = logging.getLogger(__name__)

User = get_user_model()

auth_router = Router(tags=["auth", "private"])


# ── Schemas ──────────────────────────────────────────────────────────


class AuthStatusSchema(Schema):
    is_authenticated: bool
    id: Optional[int] = None
    username: Optional[str] = None


class LogoutResponseSchema(Schema):
    is_authenticated: bool = False
    logout_url: str = ""


class ErrorSchema(Schema):
    detail: str


# ── Helpers ──────────────────────────────────────────────────────────


def _extract_session_id(access_token: str) -> str:
    """Extract the ``sid`` claim from a WorkOS access token JWT."""
    try:
        payload = access_token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return claims.get("sid", "")
    except IndexError, ValueError, json.JSONDecodeError:
        return ""


def _generate_username(email: str) -> str:
    """Derive a unique username from an email address."""
    base = email.split("@")[0]
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username


def get_or_create_django_user(workos_user):
    """Match or create a Django User from a WorkOS user profile.

    Matching priority:
    1. By workos_user_id on UserProfile (returning user)
    2. By verified email if exactly one local user matches (links accounts)
    3. Create new user (self-registration)
    """
    # 1. Exact match on WorkOS user ID
    try:
        profile = UserProfile.objects.select_related("user").get(
            workos_user_id=workos_user.id,
        )
        return profile.user
    except UserProfile.DoesNotExist:
        pass

    # 2. Match by verified email — only if unambiguous
    if workos_user.email_verified:
        matches = User.objects.filter(email=workos_user.email)
        if matches.count() == 1:
            user = matches.get()
            user.profile.workos_user_id = workos_user.id
            user.profile.save(update_fields=["workos_user_id"])
            return user

    # 3. Create new user
    user = User.objects.create_user(
        username=_generate_username(workos_user.email),
        email=workos_user.email,
        first_name=workos_user.first_name or "",
        last_name=workos_user.last_name or "",
    )
    # Profile auto-created by post_save signal
    user.profile.workos_user_id = workos_user.id
    user.profile.save(update_fields=["workos_user_id"])
    return user


# ── Endpoints ────────────────────────────────────────────────────────


@auth_router.get("/me/", response=AuthStatusSchema)
def auth_me(request):
    """Return current session's authentication state.

    Always succeeds (no auth required). Returns is_authenticated=False for
    anonymous users.
    """
    if request.user.is_authenticated:
        return {
            "is_authenticated": True,
            "id": request.user.id,
            "username": request.user.username,
        }
    return {"is_authenticated": False}


@auth_router.get("/login/", url_name="workos_login", include_in_schema=False)
def auth_login(request):
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
            client_id=settings.WORKOS_CLIENT_ID,
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
def auth_callback(request):
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
            client_id=settings.WORKOS_CLIENT_ID,
        )
    except Exception:
        log.exception("WorkOS code exchange failed")
        return HttpResponseBadRequest(
            "Authentication failed. The login link may have expired — please try again."
        )

    user = get_or_create_django_user(auth_response.user)

    # Store WorkOS session ID in the Django session (per-browser, not per-user)
    sid = _extract_session_id(auth_response.access_token)
    if sid:
        request.session["workos_session_id"] = sid

    login(request, user, backend="apps.accounts.backends.WorkOSBackend")
    return HttpResponseRedirect(next_url)


@auth_router.post("/logout/", response=LogoutResponseSchema)
def auth_logout(request):
    """End the current session and return the WorkOS logout URL if available."""
    workos_session_id = request.session.get("workos_session_id", "")
    logout(request)

    logout_url = ""
    if workos_session_id and settings.WORKOS_API_KEY and settings.WORKOS_CLIENT_ID:
        try:
            client = get_workos_client()
            logout_url = client.user_management.get_logout_url(
                session_id=workos_session_id,
            )
        except Exception:
            log.exception("Failed to generate WorkOS logout URL")

    return {"is_authenticated": False, "logout_url": logout_url}
