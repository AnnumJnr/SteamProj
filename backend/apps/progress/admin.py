"""
Django admin registration for the progress app.
"""

from django.contrib import admin

from .models import UserProgress, UserSavedItems


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "status", "completed_at", "created_at")
    list_filter = ("status",)
    search_fields = ("user__email", "course__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserSavedItems)
class UserSavedItemsAdmin(admin.ModelAdmin):
    list_display = ("user", "item_type", "course", "combo", "created_at")
    list_filter = ("item_type",)
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")