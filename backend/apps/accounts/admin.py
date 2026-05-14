from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin[User]):
    # AbstractUser's admin keys off `username` as the login field; we log in
    # by email, so reorder fieldsets accordingly.
    ordering = ("email",)
    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    search_fields = ("email", "username", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", "first_name", "last_name")}),
        ("Identity", {"fields": ("workos_user_id", "last_seen_at", "priority")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    # Operators type the username explicitly. Reserved-list enforcement
    # will live in the user-facing signup endpoint, not on this admin form
    # — admin is operator-run and reserved handles like `admin` are
    # legitimate there (e.g. for a system service account). Format and
    # uniqueness apply via the field's validators and unique constraint.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )
    # workos_user_id and last_seen_at are identity/system state, not
    # admin-editable preferences. Re-binding workos_user_id by hand could
    # silently re-point a row to a different external account; if it ever
    # legitimately needs to change, that's a dedicated admin action, not a
    # form field.
    readonly_fields = ("workos_user_id", "last_seen_at")
