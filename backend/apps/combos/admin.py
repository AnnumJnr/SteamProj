"""
Django admin registration for the combos app.

Enhancements over the Phase 1 stub:
  - ComboCourseInline uses autocomplete_fields so curators search courses
    by title instead of entering a raw UUID.
  - ComboAdmin uses fieldsets organised around the natural curation workflow.
  - List view adds computed columns: course_count, avg_rating, visibility badge.
  - Actions extended: make_private added; all actions log and return feedback.
  - ComboRatingAdmin is fully read-only (ratings come from users, not admin entry).
"""

import logging

from django.contrib import admin, messages
from django.db.models import Avg, Count
from django.utils.html import format_html

from .models import Combo, ComboCourse, ComboRating

logger = logging.getLogger(__name__)


# ─── Inline ────────────────────────────────────────────────────────────────────

class ComboCourseInline(admin.TabularInline):
    """
    Inline editor for attaching and ordering courses inside a Combo.

    autocomplete_fields replaces the plain FK widget with a live search
    popup that queries CourseAdmin.search_fields (title, instructor, tags).
    CourseAdmin already declares search_fields in courses/admin.py — no
    change is needed there.
    """

    model = ComboCourse
    extra = 1
    min_num = 0
    autocomplete_fields = ["course"]
    fields = ("order", "course", "is_required", "note")
    ordering = ("order",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("course")
            .order_by("order")
        )


# ─── Admin actions ─────────────────────────────────────────────────────────────
# Defined as module-level functions (not instance methods) so their label
# in the action dropdown does not show a class prefix.

@admin.action(description="✓  Mark selected combos as featured")
def make_featured(modeladmin, request, queryset):
    updated = queryset.update(is_featured=True)
    modeladmin.message_user(
        request,
        f"{updated} combo(s) marked as featured.",
        messages.SUCCESS,
    )
    logger.info("Admin: make_featured applied to %d combo(s).", updated)


@admin.action(description="✗  Remove featured status from selected combos")
def remove_featured(modeladmin, request, queryset):
    updated = queryset.update(is_featured=False)
    modeladmin.message_user(
        request,
        f"{updated} combo(s) removed from featured.",
        messages.SUCCESS,
    )
    logger.info("Admin: remove_featured applied to %d combo(s).", updated)


@admin.action(description="◎  Make selected combos public")
def make_public(modeladmin, request, queryset):
    updated = queryset.update(is_public=True)
    modeladmin.message_user(
        request,
        f"{updated} combo(s) are now public.",
        messages.SUCCESS,
    )
    logger.info("Admin: make_public applied to %d combo(s).", updated)


@admin.action(description="◉  Make selected combos private")
def make_private(modeladmin, request, queryset):
    updated = queryset.update(is_public=False)
    modeladmin.message_user(
        request,
        f"{updated} combo(s) are now private.",
        messages.SUCCESS,
    )
    logger.info("Admin: make_private applied to %d combo(s).", updated)


# ─── ComboAdmin ────────────────────────────────────────────────────────────────

@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    """
    Main admin for curating Combos.

    Fieldsets mirror the natural curation workflow:
      1. Identity     — name, descriptions, who it is for
      2. Outcomes     — what learners gain from completing it
      3. Structure    — difficulty, age group, estimated duration
      4. Taxonomy     — category, sub-category, tags
      5. Visibility   — public / featured / created_by flags
      6. Audit        — read-only timestamps and UUID (collapsed by default)
    """

    inlines = [ComboCourseInline]
    actions = [make_featured, remove_featured, make_public, make_private]

    # ── List view ──────────────────────────────────────────────────────────────

    list_display = (
        "title",
        "category",
        "difficulty",
        "recommended_age",
        "created_by_type",
        "course_count",
        "avg_rating_display",
        "visibility_badge",
        "created_at",
    )
    list_filter = (
        "is_featured",
        "is_public",
        "created_by_type",
        "difficulty",
        "recommended_age",
        "category",
    )
    search_fields = ("title", "tags", "short_description")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

    # ── Fieldsets (detail / edit view) ────────────────────────────────────────

    fieldsets = (
        (
            "Identity",
            {
                "description": (
                    "Public-facing name and descriptions. "
                    "Short description appears on combo cards. "
                    "Full description and overview appear on the detail page."
                ),
                "fields": (
                    "title",
                    "short_description",
                    "full_description",
                    "overview",
                    "who_is_this_for",
                ),
            },
        ),
        (
            "Outcomes",
            {
                "description": (
                    "What learners will be able to do after completing this Combo. "
                    "Be specific — these appear on the detail page and influence discovery."
                ),
                "fields": (
                    "learning_outcomes",
                    "skills_gained",
                    "prerequisites",
                    "learning_path_explanation",
                ),
            },
        ),
        (
            "Structure",
            {
                "fields": (
                    "difficulty",
                    "recommended_age",
                    "estimated_weeks",
                    "estimated_hours_per_week",
                ),
            },
        ),
        (
            "Taxonomy",
            {
                "fields": (
                    "category",
                    "sub_category",
                    "tags",
                ),
            },
        ),
        (
            "Visibility",
            {
                "description": (
                    "Public combos are visible to all users. "
                    "Featured combos appear on the homepage and discovery sections. "
                    "Set created_by_type to 'system' for all org-curated combos."
                ),
                "fields": (
                    "is_public",
                    "is_featured",
                    "created_by_type",
                    "created_by_user",
                ),
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )

    # ── Computed list columns ──────────────────────────────────────────────────

    @admin.display(description="Courses")
    def course_count(self, obj):
        """Number of courses attached to this Combo. Uses annotated value — no extra query."""
        return obj.course_count_annotation

    @admin.display(description="Avg rating")
    def avg_rating_display(self, obj):
        """Formatted average user rating, or a dash if no ratings exist yet."""
        avg = obj.avg_rating_annotation
        if avg is None:
            return "—"
        return f"{avg:.1f} ★"

    @admin.display(description="Visibility")
    def visibility_badge(self, obj):
        """
        Coloured HTML badge showing the combo's current public/featured state.

        Four states:
          Featured (green)         — public and promoted on the homepage
          Public (blue)            — visible to all, not promoted
          Featured+Private (amber) — misconfigured; should not normally exist
          Private (grey)           — only visible to the creator and admins
        """
        if obj.is_featured and obj.is_public:
            colour = "#2e7d32"
            label = "Featured"
        elif obj.is_public:
            colour = "#1565c0"
            label = "Public"
        elif obj.is_featured and not obj.is_public:
            # Warn visually — featured but private is a misconfigured state.
            colour = "#e65100"
            label = "Featured (private!)"
        else:
            colour = "#757575"
            label = "Private"

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

    # ── Queryset — attach annotations used by computed columns ─────────────────

    def get_queryset(self, request):
        """
        Annotate with course_count and avg_rating so computed list columns
        do not issue a separate query per row (avoids N+1).
        """
        return (
            super()
            .get_queryset(request)
            .prefetch_related("courses")
            .annotate(
                course_count_annotation=Count("combo_courses", distinct=True),
                avg_rating_annotation=Avg("ratings__rating"),
            )
        )


# ─── ComboCourseAdmin ──────────────────────────────────────────────────────────

@admin.register(ComboCourse)
class ComboCourseAdmin(admin.ModelAdmin):
    """
    Standalone view of the Combo↔Course junction table.

    Useful for:
      - Auditing the order of courses across all combos at once
      - Editing notes on individual combo steps without opening each combo
      - Checking which combos contain a specific course

    autocomplete_fields on both 'course' and 'combo' means the search popup
    works in both directions when adding rows directly from this view.
    """

    list_display = ("combo", "course", "order", "is_required")
    list_filter = ("is_required", "combo__category")
    search_fields = ("combo__title", "course__title")
    ordering = ("combo", "order")
    autocomplete_fields = ["course", "combo"]


# ─── ComboRatingAdmin ──────────────────────────────────────────────────────────

@admin.register(ComboRating)
class ComboRatingAdmin(admin.ModelAdmin):
    """
    Read-only view of user-submitted combo ratings.

    Ratings are created and managed by users through the API.
    The admin panel is for visibility and auditing only — no
    add, change, or delete permissions are granted here.
    """

    list_display = ("combo", "user", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("combo__title", "user__email")
    readonly_fields = ("combo", "user", "rating", "created_at", "updated_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False