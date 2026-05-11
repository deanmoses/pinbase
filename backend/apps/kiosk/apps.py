from django.apps import AppConfig


class KioskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.kiosk"
    label = "kiosk"
    verbose_name = "Kiosk"

    def ready(self) -> None:
        from . import authz  # noqa: F401  # registers authz rules at startup
