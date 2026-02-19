from django.contrib import admin

from .models import (
    Claim,
    DesignCredit,
    Manufacturer,
    ManufacturerEntity,
    Person,
    PinballModel,
    Source,
)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "priority", "url")
    list_filter = ("source_type",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class ClaimInline(admin.TabularInline):
    model = Claim
    extra = 0
    readonly_fields = (
        "source",
        "field_name",
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
    model = DesignCredit
    extra = 1
    autocomplete_fields = ("person",)


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        "model",
        "field_name",
        "value_truncated",
        "source",
        "is_active",
        "created_at",
    )
    list_filter = ("source", "is_active", "field_name")
    search_fields = ("model__name", "field_name")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("model", "source")

    @admin.display(description="Value")
    def value_truncated(self, obj):
        s = str(obj.value)
        if len(s) > 80:
            return s[:80] + "..."
        return s

    def save_model(self, request, obj, form, change):
        """Route creates through assert_claim to preserve the superseding invariant."""
        if not change:
            created = Claim.objects.assert_claim(
                model=obj.model,
                source=obj.source,
                field_name=obj.field_name,
                value=obj.value,
                citation=obj.citation,
            )
            obj.pk = created.pk
        else:
            super().save_model(request, obj, form, change)


class ManufacturerEntityInline(admin.TabularInline):
    model = ManufacturerEntity
    extra = 0
    fields = ("name", "ipdb_manufacturer_id", "years_active")


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "trade_name",
        "opdb_manufacturer_id",
        "entity_count",
    )
    search_fields = ("name", "trade_name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ManufacturerEntityInline,)

    @admin.display(description="Entities")
    def entity_count(self, obj):
        return obj.entities.count()


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "credit_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Credits")
    def credit_count(self, obj):
        return obj.credits.count()


@admin.register(PinballModel)
class PinballModelAdmin(admin.ModelAdmin):
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
    autocomplete_fields = ("manufacturer",)
    inlines = (DesignCreditInline, ClaimInline)

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "slug", "manufacturer", "year", "month"),
            },
        ),
        (
            "Specifications",
            {
                "fields": (
                    "machine_type",
                    "display_type",
                    "player_count",
                    "theme",
                    "production_quantity",
                    "mpu",
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
