"""
Django admin registration for the courses app.

Changes from Phase 1:
- Added language_status coloured badge to list display
- Added language_status and language_rejection_reason to list_filter
- Added language_rejection_reason as a read-only field in the detail view
- Added bulk admin actions: accept_language, reject_language, flag_for_review
- get_queryset() lifted to show ALL courses including rejected ones so admins
  can review and override — the public API queryset (CourseQueryset.get_active)
  handles the public filtering separately.

The admin is the primary tool for reviewing flagged courses and overriding
pipeline decisions. The workflow is:
  1. Run flag_language_status management command
  2. Go to /admin/courses/course/?language_status=flagged
  3. Open each course, check the content, change language_status, save.
"""

import logging

from django.contrib import admin, messages
from django.utils.html import format_html

from .models import Course

logger = logging.getLogger(__name__)


# ─── Admin Actions ────────────────────────────────────────────────────────────

@admin.action(description="✓  Mark selected courses as language ACCEPTED")
def accept_language(modeladmin, request, queryset):
    updated = queryset.update(
        language_status=Course.LanguageStatus.ACCEPTED,
        language_rejection_reason="",
    )
    modeladmin.message_user(
        request,
        f"{updated} course(s) marked as language accepted.",
        messages.SUCCESS,
    )
    logger.info("Admin: accept_language applied to %d course(s).", updated)


@admin.action(description="✗  Mark selected courses as language REJECTED")
def reject_language(modeladmin, request, queryset):
    updated = queryset.update(
        language_status=Course.LanguageStatus.REJECTED,
        language_rejection_reason="manually_rejected_by_admin",
    )
    modeladmin.message_user(
        request,
        f"{updated} course(s) marked as language rejected (hidden from catalog).",
        messages.WARNING,
    )
    logger.info("Admin: reject_language applied to %d course(s).", updated)


@admin.action(description="⚑  Flag selected courses for language REVIEW")
def flag_for_review(modeladmin, request, queryset):
    updated = queryset.update(
        language_status=Course.LanguageStatus.FLAGGED,
    )
    modeladmin.message_user(
        request,
        f"{updated} course(s) flagged for language review.",
        messages.WARNING,
    )
    logger.info("Admin: flag_for_review applied to %d course(s).", updated)


# ─── CourseAdmin ──────────────────────────────────────────────────────────────

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "provider",
        "category",
        "level",
        "age_group",
        "language_status_badge",
        "is_free",
        "is_active",
        "created_at",
    )
    list_filter = (
        "language_status",   # Most important filter — use this to find flagged/rejected
        "provider",
        "category",
        "level",
        "age_group",
        "format",
        "is_active",
        "is_free",
    )
    search_fields = ("title", "instructor", "tags")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "search_vector",
        "language_rejection_reason",  # Read-only — set by pipeline, overridden via dropdown
    )
    ordering = ("-created_at",)
    actions = [accept_language, reject_language, flag_for_review]

    fieldsets = (
        (
            "Core",
            {
                "fields": (
                    "id", "title", "short_description",
                    "full_description", "thumbnail_url",
                ),
            },
        ),
        (
            "Provider",
            {
                "fields": (
                    "provider", "provider_type", "source_url", "instructor",
                ),
            },
        ),
        (
            "Taxonomy",
            {
                "fields": (
                    "category", "sub_category", "tags",
                    "level", "age_group", "language", "format",
                ),
            },
        ),
        (
            "Duration",
            {
                "fields": ("duration_hours", "duration_minutes"),
            },
        ),
        (
            "Access",
            {
                "fields": ("is_free", "certificate_available", "is_active"),
            },
        ),
        (
            "Language Quality",
            {
                "description": (
                    "Set by the multi-layer language detection pipeline. "
                    "To override a pipeline decision: change language_status "
                    "using the dropdown and save. The rejection reason field is "
                    "read-only and records why the pipeline made its decision."
                ),
                "fields": ("language_status", "language_rejection_reason"),
            },
        ),
        (
            "Ratings (from source)",
            {
                "fields": ("rating_average", "rating_count"),
            },
        ),
        (
            "Source Metadata",
            {
                "classes": ("collapse",),
                "fields": ("source_metadata",),
            },
        ),
        (
            "Timestamps",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    # ── Language status badge ──────────────────────────────────────────────────

    @admin.display(description="Language")
    def language_status_badge(self, obj):
        """
        Coloured badge showing the course's language quality status.

        Green  = Accepted   — confirmed English, visible in catalog
        Grey   = Unknown    — not yet screened
        Amber  = Flagged    — uncertain, visible but needs human review
        Red    = Rejected   — non-English, hidden from catalog
        """
        colours = {
            Course.LanguageStatus.ACCEPTED: ("#2e7d32", "Accepted"),
            Course.LanguageStatus.UNKNOWN:  ("#757575", "Unknown"),
            Course.LanguageStatus.FLAGGED:  ("#e65100", "Flagged ⚑"),
            Course.LanguageStatus.REJECTED: ("#b71c1c", "Rejected ✗"),
        }
        colour, label = colours.get(
            obj.language_status,
            ("#757575", obj.language_status),
        )
        return format_html(
            '<span style="'
            "background:{colour};"
            "color:#fff;"
            "padding:2px 10px;"
            "border-radius:12px;"
            "font-size:11px;"
            "font-weight:600;"
            '">{label}</span>',
            colour=colour,
            label=label,
        )

    def get_queryset(self, request):
        """
        Admin shows ALL courses regardless of language_status or is_active.

        The public API uses CourseQueryset.get_active() which applies the
        language_status filter. The admin must see everything — including
        rejected courses — so humans can review and override pipeline decisions.
        """
        return Course.objects.all()