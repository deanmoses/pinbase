from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Core"

    def ready(self) -> None:
        from . import checks  # noqa: F401 — registers system checks
        from .authz import (
            checks as authz_checks,  # noqa: F401 — registers system checks
        )
        from .authz import rules  # noqa: F401 — registers core-owned activities
