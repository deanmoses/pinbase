from django.conf import settings
from ninja import NinjaAPI

from apps.accounts.api import auth_router
from apps.catalog.api import (
    awards_router,
    groups_router,
    manufacturers_router,
    models_router,
    people_router,
)
from apps.provenance.api import sources_router

api = NinjaAPI(
    title="Pinbase API",
    urls_namespace="api",
)


@api.get("/health")
def health(request):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    if not settings.DEBUG:
        if not (settings.FRONTEND_BUILD_DIR / "200.html").is_file():
            raise RuntimeError("Frontend build missing")
    return {"status": "ok"}


api.add_router("/auth/", auth_router)
api.add_router("/models/", models_router)
api.add_router("/groups/", groups_router)
api.add_router("/manufacturers/", manufacturers_router)
api.add_router("/people/", people_router)
api.add_router("/awards/", awards_router)
api.add_router("/sources/", sources_router)
