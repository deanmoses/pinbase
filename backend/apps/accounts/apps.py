from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self) -> None:
        # Patch AnonymousUser with the email_verified attribute the
        # PolicyUser Protocol declares. Django ships AnonymousUser.is_active
        # = False as a class attribute (visible to django-stubs); we add
        # email_verified at runtime so anonymous requests structurally
        # satisfy PolicyUser without forking django-stubs. The contract is
        # asserted in test_authz_predicates so a missing patch fails loud.
        from django.contrib.auth.models import AnonymousUser

        AnonymousUser.email_verified = False  # type: ignore[attr-defined]
