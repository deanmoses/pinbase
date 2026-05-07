from __future__ import annotations

import re
from typing import Any, ClassVar

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as BaseUserManager
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import field_not_blank


def derive_username(email: str) -> str:
    """Derive a clean URL-safe username slug from an email address.

    Lowercase the local part, replace `.`/`_`/`+` with `-`, drop anything
    outside `[a-z0-9-]`, collapse repeated hyphens, trim leading/trailing
    hyphens. Narrower than UnicodeUsernameValidator allows but well within it.
    Caller is responsible for resolving collisions.
    """
    base = email.split("@", 1)[0].lower()
    base = re.sub(r"[._+]", "-", base)
    base = re.sub(r"[^a-z0-9-]", "", base)
    base = re.sub(r"-+", "-", base).strip("-")
    # Cap to the field's max_length, leaving headroom for the "-N" suffix
    # that the unique-username resolver may append.
    base = base[:140].rstrip("-")
    return base or "user"


class UserManager(BaseUserManager["User"]):
    """Custom manager: login is by email; username is derived, not supplied."""

    use_in_migrations = True

    def derive_unique_username(self, email: str) -> str:
        """Pick an unused username slug for *email*.

        Best-effort under contention: two concurrent callers may both pick the
        same slug; the second hits the unique-index IntegrityError, and the
        caller is responsible for retrying. Single source of truth — admin,
        manager, and the WorkOS callback all route through here.
        """
        base = derive_username(email)
        candidate = base
        n = 1
        while self.filter(username=candidate).exists():
            suffix = f"-{n}"
            # Respect username max_length=150 even when *base* was length-capped
            # to 140; long suffixes still fit.
            candidate = f"{base[: 150 - len(suffix)]}{suffix}"
            n += 1
        return candidate

    def get_by_natural_key(self, username: str | None) -> User:
        """Look up a user for password authentication.

        Override of BaseUserManager.get_by_natural_key (exact match) — our
        emails are case-insensitively unique by Lower("email") constraint,
        and admin password login must match that contract or
        Alice@example.com can't log in as alice@example.com.
        """
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})

    def _create_user(
        self,
        email: str,
        password: str | None,
        **extra_fields: Any,  # noqa: ANN401 - Django manager pattern.
    ) -> User:
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        if "username" not in extra_fields:
            extra_fields["username"] = self.derive_unique_username(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    # Signature override is intentional: USERNAME_FIELD = "email", so the
    # first positional is the email, not the username (username is derived).
    def create_user(  # type: ignore[override]
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,  # noqa: ANN401 - Django manager pattern.
    ) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(  # type: ignore[override]
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,  # noqa: ANN401 - Django manager pattern.
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    # AbstractUser provides:
    #   username, first_name, last_name, email,
    #   is_active, is_staff, is_superuser, last_login, date_joined, password
    #
    # `username` is the public URL slug (/users/<username>), defaulted from
    # the email prefix at first login and editable on the settings page.

    # Redeclared to flip AbstractUser's blank=True to blank=False. Uniqueness
    # is enforced case-insensitively by the Lower("email") UniqueConstraint
    # below; casing is preserved on save (manager only normalizes the domain).
    email = models.EmailField()

    # WorkOS-side user row pointer. null=True only for the soft-delete window:
    # the user.deleted webhook clears this so a returning user can re-bind at
    # reactivation time.
    workos_user_id = models.CharField(max_length=64, null=True, blank=True, unique=True)

    # Request-time freshness signal (see ProviderSwitching.md).
    last_seen_at = models.DateTimeField(null=True, blank=True)

    # Wikipedia-style attribution priority.
    priority = models.PositiveSmallIntegerField(default=10000)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # createsuperuser will prompt for email + password only.

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_unique_email_ci",
            ),
            field_not_blank("email"),
            field_not_blank("workos_user_id"),
        ]

    def __str__(self) -> str:
        return self.username or self.email
