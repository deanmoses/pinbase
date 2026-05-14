"""WorkOS → local User lookup/refresh helpers for the auth callback.

Pure functions (modulo DB I/O): given a `WorkOSUser` from the provider,
either return an already-linked local row (refreshing mirrored fields)
or raise `LoginRefusedError` when the inbound login cannot be honored.
Returning `None` means "no match; the caller should start onboarding."
"""

from __future__ import annotations

import logging

from apps.accounts.models import User
from apps.accounts.pending import WorkOSUser

from .auth_codes import LoginRefusedError

log = logging.getLogger(__name__)


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
    raise LoginRefusedError(
        "account_conflict", "Account conflict; contact an administrator."
    )


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
            raise LoginRefusedError("account_disabled", "Account is disabled.")
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
                raise LoginRefusedError(
                    "account_conflict", "Account conflict; contact an administrator."
                )
            if not workos_user.email_verified:
                raise LoginRefusedError(
                    "email_unverified",
                    "Please verify your email with the identity provider before signing in.",
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
            "email_unverified",
            "Please verify your email with the identity provider before signing in.",
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
