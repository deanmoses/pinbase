from django.apps import AppConfig


class CitationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.citation"
    verbose_name = "Citation"

    def ready(self) -> None:
        from . import authz  # noqa: F401  # registers authz rules at startup
