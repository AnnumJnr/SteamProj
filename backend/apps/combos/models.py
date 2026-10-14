"""
Combo models.

Combo        — a structured learning path composed of ordered courses
ComboCourse  — junction table linking a Combo to its Courses (with order)
ComboRating  — user ratings for combos (1-5 stars)

Key decisions (master reference §3):
- User-created Combos are private by default (is_public=False)
- Admin can feature any public Combo (is_featured=True)
- Users rate Combos on the platform (not courses)
"""

import logging

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import TimestampedModel
from apps.courses.models import Course

logger = logging.getLogger(__name__)


class Combo(TimestampedModel):
    """
    A structured learning path built from an ordered set of courses.
    The key differentiator of the platform (master reference §1).

    Can be created by:
    - admin: staff-curated, featured paths
    - system: auto-generated (Phase 2+)
    - user: custom user-built paths (private by default)
    """

    class CreatedBy(models.TextChoices):
        ADMIN = "admin", "Admin"
        SYSTEM = "system", "System"
        USER = "user", "User"

    class Difficulty(models.TextChoices):
        BEGINNER = "Beginner", "Beginner"
        INTERMEDIATE = "Intermediate", "Intermediate"
        ADVANCED = "Advanced", "Advanced"
        MIXED = "Mixed", "Mixed"

    class RecommendedAge(models.TextChoices):
        KIDS = "Kids", "Kids (under 13)"
        TEENS = "Teens", "Teens (13–17)"
        ADULTS = "Adults", "Adults (18--)"
        ALL_AGES = "All Ages", "All Ages"

    # ─── Ownership ────────────────────────────────────────────────────────────

    created_by_type = models.CharField(
        max_length=10,
        choices=CreatedBy.choices,
        default=CreatedBy.USER,
        help_text="Whether this Combo was created by admin, system, or a user.",
    )
    created_by_user = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="combos",
        help_text="The user who created this Combo. Null for admin/system-created Combos.",
    )

    # ─── Core Content ─────────────────────────────────────────────────────────

    title = models.CharField(max_length=300)
    short_description = models.TextField(
        blank=True,
        default="",
        max_length=300,
        help_text="Short summary shown in combo cards.",
    )
    full_description = models.TextField(
        blank=True,
        default="",
    )
    overview = models.TextField(
        blank=True,
        default="",
        help_text="High-level overview of what this learning path covers.",
    )
    who_is_this_for = models.TextField(
        blank=True,
        default="",
        help_text="Description of the intended learner audience.",
    )
    learning_outcomes = models.JSONField(
        default=list,
        blank=True,
        help_text="What learners will be able to do after completing this Combo.",
    )
    prerequisites = models.JSONField(
        default=list,
        blank=True,
        help_text="Knowledge or skills required before starting this Combo.",
    )
    skills_gained = models.JSONField(
        default=list,
        blank=True,
        help_text="Specific skills acquired upon completion.",
    )
    learning_path_explanation = models.TextField(
        blank=True,
        default="",
        help_text="Explanation of why the courses are ordered the way they are.",
    )

    # ─── Taxonomy ─────────────────────────────────────────────────────────────

    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Primary STEM category for this Combo.",
    )
    sub_category = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER,
    )
    recommended_age = models.CharField(
        max_length=10,
        choices=RecommendedAge.choices,
        default=RecommendedAge.ALL_AGES,
    )
    tags = models.JSONField(
        default=list,
        blank=True,
    )

    # ─── Duration Estimate ────────────────────────────────────────────────────

    estimated_weeks = models.PositiveIntegerField(
        default=0,
        help_text="Estimated total weeks to complete this Combo.",
    )
    estimated_hours_per_week = models.PositiveIntegerField(
        default=0,
        help_text="Recommended hours per week to complete within the estimated timeframe.",
    )

    # ─── Visibility & Featuring ───────────────────────────────────────────────

    is_public = models.BooleanField(
        default=False,
        help_text="User-created Combos are private by default. Must be explicitly shared.",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Admin-featured Combos appear prominently on the platform.",
    )

    # ─── Courses (via junction table) ─────────────────────────────────────────

    courses = models.ManyToManyField(
        Course,
        through="ComboCourse",
        related_name="combos",
        blank=True,
    )

    class Meta:
        verbose_name = "Combo"
        verbose_name_plural = "Combos"
        db_table = "combos"
        indexes = [
            models.Index(fields=["is_public"], name="idx_combo_public"),
            models.Index(fields=["is_featured"], name="idx_combo_featured"),
            models.Index(fields=["category"], name="idx_combo_category"),
            models.Index(fields=["created_by_type"], name="idx_combo_creator_type"),
        ]

    def __str__(self):
        return self.title


class ComboCourse(TimestampedModel):
    """
    Junction table linking a Combo to its Courses.
    Stores ordering and whether a course is required within the Combo.

    Order is 1-indexed and must be unique within a Combo.
    """

    combo = models.ForeignKey(
        Combo,
        on_delete=models.CASCADE,
        related_name="combo_courses",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="combo_courses",
    )
    order = models.PositiveIntegerField(
        help_text="1-indexed position of this course in the Combo.",
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this course is mandatory within the Combo.",
    )
    note = models.TextField(
        blank=True,
        default="",
        help_text="Curator note explaining why this course is at this position.",
    )

    class Meta:
        verbose_name = "Combo Course"
        verbose_name_plural = "Combo Courses"
        db_table = "combo_courses"
        unique_together = [("combo", "order")]   # Enforce unique order per Combo
        ordering = ["order"]

    def __str__(self):
        return f"{self.combo.title} — Step {self.order}: {self.course.title}"


class ComboRating(TimestampedModel):
    """
    User rating for a Combo (1–5 stars).
    One rating per user per Combo (enforced via unique_together).

    Master reference §3: "User ratings on platform (1–5 stars). Stored in ComboRating."
    Courses are not rated by users on this platform.
    """

    combo = models.ForeignKey(
        Combo,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="combo_ratings",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 (lowest) to 5 (highest).",
    )
    review = models.TextField(
        blank=True,
        default="",
        max_length=1000,
        help_text="Optional written review alongside the star rating.",
    )

    class Meta:
        verbose_name = "Combo Rating"
        verbose_name_plural = "Combo Ratings"
        db_table = "combo_ratings"
        unique_together = [("combo", "user")]   # One rating per user per Combo

    def __str__(self):
        return f"{self.user.email} rated '{self.combo.title}': {self.rating}/5"