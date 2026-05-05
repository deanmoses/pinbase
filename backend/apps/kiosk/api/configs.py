"""Kiosk resource API — superuser-only CRUD over KioskConfig.

Plain Django models, no claims plumbing (kiosk configs are operational
settings, not catalog claims). See plan and docs/Provenance.md.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.responses import Status
from ninja.security import django_auth

from apps.catalog.api.schemas import EntityRef
from apps.catalog.models import Title
from apps.core.api_helpers import authed_user
from apps.core.schemas import ErrorDetailSchema
from apps.kiosk.api.schemas import (
    KioskConfigDetailSchema,
    KioskConfigItemDetailSchema,
    KioskConfigListItemSchema,
    KioskConfigPatchSchema,
)
from apps.kiosk.models import KioskConfig, KioskConfigItem

kiosk_configs_router = Router(tags=["kiosk", "private"])

_DEFAULT_NAME = "Untitled kiosk"
_AUTO_SUFFIX_MAX_RETRIES = 5


# ── Helpers ──────────────────────────────────────────────────────────


def _require_superuser(request: HttpRequest) -> None:
    """Gate every endpoint on superuser. ``django_auth`` already rejected anon."""
    user = authed_user(request)
    if not user.is_superuser:
        raise HttpError(403, "Superuser access required.")


def _serialize_item(item: KioskConfigItem) -> KioskConfigItemDetailSchema:
    return KioskConfigItemDetailSchema(
        id=item.pk,
        position=item.position,
        hook=item.hook,
        title=EntityRef(name=item.title.name, slug=item.title.slug),
    )


def _serialize_detail(config: KioskConfig) -> KioskConfigDetailSchema:
    items = list(config.items.select_related("title"))
    return KioskConfigDetailSchema(
        id=config.pk,
        name=config.name,
        page_heading=config.page_heading,
        idle_seconds=config.idle_seconds,
        items=[_serialize_item(item) for item in items],
    )


def _next_default_name() -> str:
    """Return the next free 'Untitled kiosk' / 'Untitled kiosk N' label.

    Best-effort suggestion; the caller still wraps the create in a retry loop
    in case two requests race past the same suggestion.
    """
    existing = set(
        KioskConfig.objects.filter(name__startswith=_DEFAULT_NAME).values_list(
            "name", flat=True
        )
    )
    if _DEFAULT_NAME not in existing:
        return _DEFAULT_NAME
    n = 2
    while f"{_DEFAULT_NAME} {n}" in existing:
        n += 1
    return f"{_DEFAULT_NAME} {n}"


# ── Endpoints ────────────────────────────────────────────────────────


@kiosk_configs_router.get(
    "configs/",
    auth=django_auth,
    response=list[KioskConfigListItemSchema],
)
def list_configs(request: HttpRequest) -> list[KioskConfigListItemSchema]:
    _require_superuser(request)
    configs = KioskConfig.objects.annotate(item_count=Count("items"))
    return [
        KioskConfigListItemSchema(
            id=c.pk,
            name=c.name,
            page_heading=c.page_heading,
            idle_seconds=c.idle_seconds,
            item_count=c.item_count,
        )
        for c in configs
    ]


@kiosk_configs_router.post(
    "configs/",
    auth=django_auth,
    response={201: KioskConfigDetailSchema, 409: ErrorDetailSchema},
)
def create_config(request: HttpRequest) -> Status[KioskConfigDetailSchema]:
    """Create an empty kiosk with an auto-suggested name.

    Audit fields come from ``request.user`` — we don't accept them in the
    payload. Wrapped in a retry-on-IntegrityError loop in case two superusers
    race past the same suggested name (the unique constraint would otherwise
    raise on the loser).
    """
    _require_superuser(request)
    user = authed_user(request)
    last_exc: IntegrityError | None = None
    for _ in range(_AUTO_SUFFIX_MAX_RETRIES):
        name = _next_default_name()
        try:
            with transaction.atomic():
                config = KioskConfig.objects.create(
                    name=name, created_by=user, updated_by=user
                )
            return Status(201, _serialize_detail(config))
        except IntegrityError as exc:
            last_exc = exc
            continue
    # Exhausted retries — surface the underlying constraint failure.
    raise HttpError(
        409, "Could not allocate a unique default kiosk name; please try again."
    ) from last_exc


@kiosk_configs_router.get(
    "configs/{config_id}/",
    auth=django_auth,
    response=KioskConfigDetailSchema,
)
def get_config(request: HttpRequest, config_id: int) -> KioskConfigDetailSchema:
    _require_superuser(request)
    config = get_object_or_404(KioskConfig, pk=config_id)
    return _serialize_detail(config)


@kiosk_configs_router.patch(
    "configs/{config_id}/",
    auth=django_auth,
    response={
        200: KioskConfigDetailSchema,
        404: ErrorDetailSchema,
        422: ErrorDetailSchema,
    },
)
def update_config(
    request: HttpRequest, config_id: int, data: KioskConfigPatchSchema
) -> KioskConfigDetailSchema:
    """Update scalars and/or fully replace items in one transaction."""
    _require_superuser(request)
    user = authed_user(request)
    config = get_object_or_404(KioskConfig, pk=config_id)

    with transaction.atomic():
        scalar_changed = False
        if data.name is not None and data.name != config.name:
            config.name = data.name
            scalar_changed = True
        if data.page_heading is not None and data.page_heading != config.page_heading:
            config.page_heading = data.page_heading
            scalar_changed = True
        if data.idle_seconds is not None and data.idle_seconds != config.idle_seconds:
            config.idle_seconds = data.idle_seconds
            scalar_changed = True
        config.updated_by = user
        if scalar_changed:
            try:
                config.save()
            except IntegrityError as exc:
                raise HttpError(409, str(exc)) from exc
        else:
            # Always bump audit fields + updated_at, even on items-only edits.
            config.save(update_fields=["updated_by", "updated_at"])

        if data.items is not None:
            # Full replacement avoids the (config, position) UniqueConstraint
            # footgun on naive in-place updates. List is small (10–30 items).
            slugs = [item.title_slug for item in data.items]
            titles_by_slug = {t.slug: t for t in Title.objects.filter(slug__in=slugs)}
            missing = [s for s in slugs if s not in titles_by_slug]
            if missing:
                raise HttpError(422, f"Unknown title slugs: {missing}")

            config.items.all().delete()
            KioskConfigItem.objects.bulk_create(
                [
                    KioskConfigItem(
                        config=config,
                        title=titles_by_slug[item.title_slug],
                        hook=item.hook,
                        position=item.position,
                    )
                    for item in data.items
                ]
            )

    config.refresh_from_db()
    return _serialize_detail(config)


@kiosk_configs_router.delete(
    "configs/{config_id}/",
    auth=django_auth,
    response={204: None, 404: ErrorDetailSchema},
)
def delete_config(request: HttpRequest, config_id: int) -> Status[None]:
    _require_superuser(request)
    config = get_object_or_404(KioskConfig, pk=config_id)
    config.delete()
    return Status(204, None)
