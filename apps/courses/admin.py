"""
Django admin registration for the courses app.
"""

from django.contrib import admin

from .models import Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title", "provider", "category", "level", "age_group",
        "is_free", "is_active", "created_at",
    )
    list_filter = ("provider", "category", "level", "age_group", "format", "is_active", "is_free")
    search_fields = ("title", "instructor", "tags")
    readonly_fields = ("id", "created_at", "updated_at", "search_vector")
    ordering = ("-created_at",)

    fieldsets = (
        ("Core", {"fields": ("id", "title", "short_description", "full_description", "thumbnail_url")}),
        ("Provider", {"fields": ("provider", "provider_type", "source_url", "instructor")}),
        ("Taxonomy", {"fields": ("category", "sub_category", "tags", "level", "age_group", "language", "format")}),
        ("Duration", {"fields": ("duration_hours", "duration_minutes")}),
        ("Access", {"fields": ("is_free", "certificate_available", "is_active")}),
        ("Ratings (from source)", {"fields": ("rating_average", "rating_count")}),
        ("Source Metadata", {"fields": ("source_metadata",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )