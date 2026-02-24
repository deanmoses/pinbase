from decimal import Decimal

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType

from apps.provenance.models import Claim

from .models import (
    DesignCredit,
    MachineGroup,
    MachineModel,
    Manufacturer,
    ManufacturerEntity,
    Person,
    System,
    Theme,
)
from .resolve import (
    DIRECT_FIELDS,
    MANUFACTURER_DIRECT_FIELDS,
    PERSON_DIRECT_FIELDS,
    SYSTEM_DIRECT_FIELDS,
    THEME_DIRECT_FIELDS,
    resolve_manufacturer,
    resolve_model,
    resolve_person,
    resolve_system,
    resolve_theme,
)


class ProvenanceSaveMixin:
    """Routes writes to claim-controlled fields through the provenance system.

    Subclasses define:
    - ``CLAIM_FIELDS``: frozenset of form field names that are claim-controlled.
    - ``_to_claim_value(field_name, value)``: serialize a form value for storage
      in a Claim (override for FK fields).
    - ``_resolve(obj)``: call the appropriate resolve function after asserting claims.

    On save, any changed claim-controlled field is asserted as a user Claim, then
    the object is re-resolved so the materialized fields stay consistent.
    """

    CLAIM_FIELDS: frozenset = frozenset()

    def _to_claim_value(self, field_name: str, value):
        if isinstance(value, Decimal):
            return str(value)
        return value

    def _resolve(self, obj) -> None:
        raise NotImplementedError

    def save_model(self, request, obj, form, change):
        # Persist the object first (required to have a PK for claim creation).
        super().save_model(request, obj, form, change)

        changed = [f for f in form.changed_data if f in self.CLAIM_FIELDS]
        if not changed:
            return

        for field_name in changed:
            claim_value = self._to_claim_value(
                field_name, form.cleaned_data.get(field_name)
            )
            if claim_value is None:
                # Field cleared: withdraw the user's claim rather than storing a
                # NULL value (Claim.value does not allow NULL).
                Claim.objects.filter(
                    content_type=ContentType.objects.get_for_model(obj),
                    object_id=obj.pk,
                    user=request.user,
                    field_name=field_name,
                    is_active=True,
                ).update(is_active=False)
            else:
                Claim.objects.assert_claim(
                    obj, field_name, claim_value, user=request.user
                )
        self._resolve(obj)


class ClaimInline(GenericTabularInline):
    model = Claim
    extra = 0
    readonly_fields = (
        "source",
        "field_name",
        "claim_key",
        "value",
        "citation",
        "is_active",
        "created_at",
    )
    can_delete = False
    show_change_link = True
    classes = ("collapse",)
    verbose_name_plural = "claims (provenance)"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_active=True)

    def has_add_permission(self, request, obj=None):
        return False


class DesignCreditInline(admin.TabularInline):
    """Read-only inline — credits are materialized from relationship claims."""

    model = DesignCredit
    extra = 0
    readonly_fields = ("person", "role")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ThemeInline(admin.TabularInline):
    """Read-only inline — theme tags are materialized from relationship claims."""

    model = MachineModel.themes.through
    extra = 0
    readonly_fields = ("theme",)
    can_delete = False
    verbose_name = "theme"
    verbose_name_plural = "themes"

    def has_add_permission(self, request, obj=None):
        return False


class ManufacturerEntityInline(admin.TabularInline):
    model = ManufacturerEntity
    extra = 0
    fields = ("name", "ipdb_manufacturer_id", "years_active")


@admin.register(Manufacturer)
class ManufacturerAdmin(ProvenanceSaveMixin, admin.ModelAdmin):
    CLAIM_FIELDS = frozenset(MANUFACTURER_DIRECT_FIELDS)

    def _resolve(self, obj):
        resolve_manufacturer(obj)

    list_display = (
        "name",
        "trade_name",
        "opdb_manufacturer_id",
        "entity_count",
    )
    search_fields = ("name", "trade_name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ManufacturerEntityInline, ClaimInline)

    @admin.display(description="Entities")
    def entity_count(self, obj):
        return obj.entities.count()


@admin.register(MachineGroup)
class MachineGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "opdb_id", "machine_model_count")
    search_fields = ("name", "short_name", "opdb_id")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Machine Models")
    def machine_model_count(self, obj):
        return obj.machine_models.count()


@admin.register(Theme)
class ThemeAdmin(ProvenanceSaveMixin, admin.ModelAdmin):
    CLAIM_FIELDS = frozenset(THEME_DIRECT_FIELDS)

    def _resolve(self, obj):
        resolve_theme(obj)

    list_display = ("name", "machine_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ClaimInline,)

    @admin.display(description="Machines")
    def machine_count(self, obj):
        return obj.machine_models.count()


@admin.register(System)
class SystemAdmin(ProvenanceSaveMixin, admin.ModelAdmin):
    CLAIM_FIELDS = frozenset(SYSTEM_DIRECT_FIELDS)

    def _resolve(self, obj):
        resolve_system(obj)

    list_display = ("name", "manufacturer", "machine_count")
    search_fields = ("name",)
    list_filter = ("manufacturer",)
    autocomplete_fields = ("manufacturer",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ClaimInline,)

    @admin.display(description="Machines")
    def machine_count(self, obj):
        return obj.machine_models.count()


@admin.register(Person)
class PersonAdmin(ProvenanceSaveMixin, admin.ModelAdmin):
    CLAIM_FIELDS = frozenset(PERSON_DIRECT_FIELDS)

    def _resolve(self, obj):
        resolve_person(obj)

    list_display = ("name", "credit_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ClaimInline,)

    @admin.display(description="Credits")
    def credit_count(self, obj):
        return obj.credits.count()


@admin.register(MachineModel)
class MachineModelAdmin(ProvenanceSaveMixin, admin.ModelAdmin):
    CLAIM_FIELDS = frozenset(DIRECT_FIELDS) | {"manufacturer", "group", "system"}

    def _to_claim_value(self, field_name: str, value):
        if field_name == "manufacturer" and value is not None:
            return (
                value.opdb_manufacturer_id if value.opdb_manufacturer_id else value.name
            )
        if field_name == "group" and value is not None:
            return value.opdb_id
        if field_name == "system" and value is not None:
            return value.slug
        return super()._to_claim_value(field_name, value)

    def _resolve(self, obj):
        resolve_model(obj)

    list_display = (
        "name",
        "manufacturer",
        "year",
        "machine_type",
        "display_type",
        "ipdb_id",
    )
    list_filter = ("machine_type", "display_type", "manufacturer")
    search_fields = ("name", "ipdb_id", "manufacturer__name")
    autocomplete_fields = ("manufacturer", "group", "alias_of", "system")
    inlines = (DesignCreditInline, ThemeInline, ClaimInline)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "manufacturer",
                    "group",
                    "alias_of",
                    "year",
                    "month",
                ),
            },
        ),
        (
            "Specifications",
            {
                "fields": (
                    "machine_type",
                    "display_type",
                    "player_count",
                    "production_quantity",
                    "system",
                    "flipper_count",
                ),
            },
        ),
        (
            "Cross-references",
            {
                "fields": ("ipdb_id", "opdb_id", "pinside_id"),
            },
        ),
        (
            "Ratings",
            {
                "fields": ("ipdb_rating", "pinside_rating"),
            },
        ),
        (
            "Museum Content",
            {
                "fields": ("educational_text", "sources_notes"),
                "classes": ("collapse",),
            },
        ),
        (
            "Extra Data",
            {
                "fields": ("extra_data",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {"slug": ("name",)}


@admin.register(DesignCredit)
class DesignCreditAdmin(admin.ModelAdmin):
    list_display = ("person", "role", "model")
    list_filter = ("role",)
    search_fields = ("person__name", "model__name")
    autocomplete_fields = ("person", "model")
