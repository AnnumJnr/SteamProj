"""
Django admin registration for the users app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline profile editor within the User admin page."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = ("display_name", "avatar_url", "age_group", "bio", "interests")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for the custom User model."""

    inlines = [UserProfileInline]

    list_display = ("email", "is_active", "is_staff", "is_email_verified", "created_at")
    list_filter = ("is_active", "is_staff", "is_email_verified")
    search_fields = ("email",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "is_email_verified", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active"),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Standalone admin for UserProfile (also accessible inline via UserAdmin)."""

    list_display = ("user", "display_name", "age_group", "created_at")
    list_filter = ("age_group",)
    search_fields = ("user__email", "display_name")
    readonly_fields = ("created_at", "updated_at")