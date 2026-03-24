from django.contrib import admin

from .models import Claim, Source, SourceFieldLicense


class SourceFieldLicenseInline(admin.TabularInline):
    model = SourceFieldLicense
    extra = 1


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "priority",
        "is_enabled",
        "default_license",
        "url",
    )
    list_editable = ("is_enabled", "default_license")
    list_filter = ("source_type", "is_enabled")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SourceFieldLicenseInline]


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
                user=obj.user,
                claim_key=obj.claim_key,
                license=obj.license,
            )
            obj.pk = created.pk
        else:
            super().save_model(request, obj, form, change)
