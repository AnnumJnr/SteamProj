"""
Ingestion admin.

IngestionLog is read-only in admin — logs are created only by the pipeline.
Adds a custom admin action to trigger a manual ingestion run for a source.

Rule 8: IngestionLog entries must never be edited manually — they are
        the audit trail for the pipeline.
"""

import logging

from django.contrib import admin, messages
from django.utils.html import format_html

from apps.ingestion.models import IngestionLog

logger = logging.getLogger(__name__)


@admin.register(IngestionLog)
class IngestionLogAdmin(admin.ModelAdmin):
    """
    Read-only admin view for ingestion run logs.

    The list view is the primary interface — detail view allows inspecting
    error messages and fallback reasons for failed runs.

    Custom action: trigger_manual_ingestion — queues a Celery task for
    the selected source(s).
    """

    list_display = [
        "source",
        "status_badge",
        "courses_created",
        "courses_updated",
        "courses_skipped",
        "fallback_triggered",
        "started_at",
        "duration_display",
    ]
    list_filter = ["source", "status", "fallback_triggered"]
    search_fields = ["source", "error_message", "fallback_reason"]
    ordering = ["-started_at"]
    readonly_fields = [
        "source", "status", "courses_fetched", "courses_created",
        "courses_updated", "courses_skipped", "error_message",
        "fallback_triggered", "fallback_reason", "started_at", "completed_at",
        "created_at", "updated_at",
    ]
    actions = ["trigger_manual_ingestion"]

    # ── Prevent all writes ────────────────────────────────────────────────────

    def has_add_permission(self, request):
        """IngestionLogs are created by the pipeline only — never manually."""
        return False

    def has_change_permission(self, request, obj=None):
        """IngestionLogs are immutable audit records."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Preserve audit trail — no deletion via admin."""
        return False

    # ── Display helpers ───────────────────────────────────────────────────────

    @admin.display(description="Status")
    def status_badge(self, obj: IngestionLog) -> str:
        """Render status as a colored badge for quick scanning."""
        color_map = {
            IngestionLog.Status.SUCCESS: "#28a745",
            IngestionLog.Status.PARTIAL: "#fd7e14",
            IngestionLog.Status.FALLBACK: "#ffc107",
            IngestionLog.Status.FAILED: "#dc3545",
            IngestionLog.Status.STARTED: "#007bff",
        }
        color = color_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Duration")
    def duration_display(self, obj: IngestionLog) -> str:
        """Show run duration if the run completed."""
        if obj.started_at and obj.completed_at:
            delta = obj.completed_at - obj.started_at
            total_seconds = int(delta.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            return f"{minutes}m {seconds}s"
        if obj.status == IngestionLog.Status.STARTED:
            return "Running…"
        return "—"

    # ── Admin Actions ─────────────────────────────────────────────────────────

    @admin.action(description="Trigger manual ingestion for selected source(s)")
    def trigger_manual_ingestion(self, request, queryset):
        """
        Queue a manual ingestion run for each unique source in the selection.

        Deduplicates sources so selecting 10 YouTube logs doesn't queue 10 tasks.
        Uses run_ingestion_manual (max_retries=0) for immediate feedback.

        Rule 6: Action dispatches Celery task — no pipeline logic here.
        """
        from apps.ingestion.tasks import run_ingestion_manual

        unique_sources = set(queryset.values_list("source", flat=True))
        queued = []

        for source_key in unique_sources:
            try:
                run_ingestion_manual.delay(source_key)
                queued.append(source_key)
                logger.info(
                    "IngestionLogAdmin.trigger_manual_ingestion: "
                    "Queued manual run for source='%s' by user='%s'",
                    source_key,
                    request.user.email,
                )
            except Exception as exc:
                logger.error(
                    "IngestionLogAdmin.trigger_manual_ingestion: "
                    "Failed to queue source='%s': %s",
                    source_key,
                    exc,
                )
                self.message_user(
                    request,
                    f"Failed to queue ingestion for '{source_key}': {exc}",
                    level=messages.ERROR,
                )

        if queued:
            self.message_user(
                request,
                f"Ingestion queued for: {', '.join(queued)}. Check Ingestion Logs for results.",
                level=messages.SUCCESS,
            )