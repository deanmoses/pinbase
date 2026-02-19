from django.conf import settings
from ninja import NinjaAPI

from apps.machines.api import (
    groups_router,
    manufacturers_router,
    models_router,
    people_router,
    sources_router,
)

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
        if not (settings.FRONTEND_BUILD_DIR / "index.html").is_file():
            raise RuntimeError("Frontend build missing")
    return {"status": "ok"}


api.add_router("/models/", models_router)
api.add_router("/groups/", groups_router)
api.add_router("/manufacturers/", manufacturers_router)
api.add_router("/people/", people_router)
api.add_router("/sources/", sources_router)
