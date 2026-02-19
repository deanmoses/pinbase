from ninja import NinjaAPI

from apps.machines.api import (
    manufacturers_router,
    models_router,
    people_router,
    sources_router,
)

api = NinjaAPI(
    title="svel-djang API",
    urls_namespace="api",
)


@api.get("/health")
def health(request):
    return {"status": "ok"}


api.add_router("/models/", models_router)
api.add_router("/manufacturers/", manufacturers_router)
api.add_router("/people/", people_router)
api.add_router("/sources/", sources_router)
