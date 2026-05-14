"""Auth endpoints: login redirect, OAuth callback, logout, /me."""

from __future__ import annotations

import logging
import secrets

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import AnonymousUser
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.utils.http import url_has_allowed_host_and_scheme
from ninja import Router

from apps.accounts.models import User
from apps.accounts.pending import extract_workos_session_id, put_pending
from apps.accounts.schemas import AuthStatusSchema
from apps.accounts.workos_client import get_workos_client
from apps.core.authz import compute_capability_map, policy_user
from apps.core.authz.markers import public_mutation

from .workos_match import LoginRefusedError, _try_match_existing

log = logging.getLogger(__name__)

auth_router = Router(tags=["auth", "private"])


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
