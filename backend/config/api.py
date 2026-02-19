from ninja import NinjaAPI

api = NinjaAPI(
    title="svel-djang API",
    urls_namespace="api",
)


@api.get("/health")
def health(request):
    return {"status": "ok"}
