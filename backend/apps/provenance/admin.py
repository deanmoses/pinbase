from django.contrib import admin

from .models import Claim, Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "priority", "url")
    list_filter = ("source_type",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "field_name",
        "value_truncated",
        "source",
        "is_active",
        "created_at",
    )
    list_filter = ("source", "is_active", "field_name")
    search_fields = ("field_name",)
    readonly_fields = ("content_type", "object_id", "created_at")

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
                obj.subject,
                obj.field_name,
                obj.value,
                obj.citation,
                source=obj.source,
            )
            obj.pk = created.pk
        else:
            super().save_model(request, obj, form, change)
