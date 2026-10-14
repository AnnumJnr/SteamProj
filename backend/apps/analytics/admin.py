"""
Django admin registration for the analytics app.
"""

from django.contrib import admin

from .models import EventLog


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ("event_name", "user_id", "sent_to_posthog", "fired_at")
    list_filter = ("event_name", "sent_to_posthog")
    search_fields = ("event_name", "user_id")
    readonly_fields = (
        "id", "event_name", "user_id", "properties", "context",
        "sent_to_posthog", "posthog_error", "fired_at", "created_at", "updated_at",
    )
    ordering = ("-fired_at",)

    def has_add_permission(self, request):
        # EventLog entries are append-only, created only by the event system
        return False

    def has_change_permission(self, request, obj=None):
        # Event logs are immutable
        return False