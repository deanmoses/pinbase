from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.forms import ModelForm
from django.http import HttpRequest

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
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    # workos_user_id and last_seen_at are identity/system state, not
    # admin-editable preferences. Re-binding workos_user_id by hand could
    # silently re-point a row to a different external account; if it ever
    # legitimately needs to change, that's a dedicated admin action, not a
    # form field.
    readonly_fields = ("workos_user_id", "last_seen_at")

    def save_model(
        self,
        request: HttpRequest,
        obj: User,
        form: ModelForm[User],
        change: bool,
    ) -> None:
        # The default add form (UserCreationForm) builds the instance and
        # saves it directly, bypassing UserManager._create_user — so an
        # admin-added user lands with username="" and the next add hits the
        # unique-username constraint. Derive here on first save.
        if not change and not obj.username:
            obj.username = User.objects.derive_unique_username(obj.email)
        super().save_model(request, obj, form, change)
