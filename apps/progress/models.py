"""
Progress models.

UserProgress    — tracks course completion per user (self-reported)
UserSavedItems  — saved courses and combos per user

Key decisions (master reference §3):
- Progress is self-reported (user clicks "Mark as Complete")
- Users can save both courses and combos
- No platform-side verification of actual viewing
"""

import logging

from django.db import models

from common.models import TimestampedModel

logger = logging.getLogger(__name__)


class UserProgress(TimestampedModel):
    """
    Records a user's progress on a specific course.

    Status is self-reported — the platform does not verify viewing
    (content lives on external platforms).

    One record per user per course. Status transitions:
    not_started → in_progress → completed
    """

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="progress_records",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="user_progress",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the user marked this course as complete.",
    )

    class Meta:
        verbose_name = "User Progress"
        verbose_name_plural = "User Progress Records"
        db_table = "user_progress"
        unique_together = [("user", "course")]   # One record per user per course
        indexes = [
            models.Index(fields=["user", "status"], name="idx_progress_user_status"),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.course.title}: {self.status}"


class UserSavedItems(TimestampedModel):
    """
    Saved courses and combos per user.
    Polymorphic: stores either a course or a combo reference, not both.

    Master reference §3: "Users can save both courses and combos.
    Stored in UserSavedItems table (handles both types)."
    """

    class ItemType(models.TextChoices):
        COURSE = "course", "Course"
        COMBO = "combo", "Combo"

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="saved_items",
    )
    item_type = models.CharField(
        max_length=10,
        choices=ItemType.choices,
        help_text="Whether this saved item is a course or a combo.",
    )
    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
        help_text="Populated when item_type='course'. Null otherwise.",
    )
    combo = models.ForeignKey(
        "combos.Combo",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
        help_text="Populated when item_type='combo'. Null otherwise.",
    )

    class Meta:
        verbose_name = "User Saved Item"
        verbose_name_plural = "User Saved Items"
        db_table = "user_saved_items"
        # Prevent saving the same item twice
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                condition=models.Q(item_type="course"),
                name="unique_saved_course_per_user",
            ),
            models.UniqueConstraint(
                fields=["user", "combo"],
                condition=models.Q(item_type="combo"),
                name="unique_saved_combo_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "item_type"], name="idx_saved_user_type"),
        ]

    def __str__(self):
        if self.item_type == self.ItemType.COURSE and self.course:
            return f"{self.user.email} saved course: {self.course.title}"
        if self.item_type == self.ItemType.COMBO and self.combo:
            return f"{self.user.email} saved combo: {self.combo.title}"
        return f"{self.user.email} saved item ({self.item_type})"