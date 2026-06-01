"""
Progress querysets.

All database query logic for UserProgress and UserSavedItems lives here.
Views and services must never construct raw ORM queries outside this file.

Rule 4: Query logic must be centralized.
"""

import logging

from django.db.models import Count, QuerySet

from apps.progress.models import UserProgress, UserSavedItems

logger = logging.getLogger(__name__)


class UserProgressQueryset:
    """
    All DB query logic for the UserProgress model.
    """

    @staticmethod
    def get_by_user(user_id) -> QuerySet:
        """
        Return all progress records for a user, with course pre-fetched.
        Used in the dashboard progress view.
        """
        return (
            UserProgress.objects.filter(user_id=user_id)
            .select_related("course")
            .order_by("-updated_at")
        )

    @staticmethod
    def get_by_user_and_course(user_id, course_id) -> UserProgress | None:
        """
        Return the progress record for a specific user+course pair, or None.
        Used when marking a course as complete or checking current status.
        """
        try:
            return UserProgress.objects.get(user_id=user_id, course_id=course_id)
        except UserProgress.DoesNotExist:
            return None

    @staticmethod
    def get_completed_by_user(user_id) -> QuerySet:
        """Return all completed course progress records for a user."""
        return (
            UserProgress.objects.filter(
                user_id=user_id, status=UserProgress.Status.COMPLETED
            )
            .select_related("course")
            .order_by("-completed_at")
        )

    @staticmethod
    def get_in_progress_by_user(user_id) -> QuerySet:
        """Return all in-progress course records for a user."""
        return (
            UserProgress.objects.filter(
                user_id=user_id, status=UserProgress.Status.IN_PROGRESS
            )
            .select_related("course")
            .order_by("-updated_at")
        )

    @staticmethod
    def get_completed_course_ids_for_user(user_id) -> set:
        """
        Return a set of course IDs that the user has completed.
        Used for combo progress calculation.

        MULTI-USE: Used by:
        1. Dashboard progress view — called from progress/views.py
        2. Combo progress calculation — called from combos/services.py → get_combo_progress()
        CAUTION: Changes here affect both flows above.
        """
        return set(
            UserProgress.objects.filter(
                user_id=user_id, status=UserProgress.Status.COMPLETED
            ).values_list("course_id", flat=True)
        )

    @staticmethod
    def get_summary_for_user(user_id) -> dict:
        """
        Return aggregate progress counts for a user.
        Used in the dashboard overview.
        Returns: { not_started, in_progress, completed }
        """
        records = UserProgress.objects.filter(user_id=user_id)
        counts = records.values("status").annotate(count=Count("status"))
        summary = {
            UserProgress.Status.NOT_STARTED: 0,
            UserProgress.Status.IN_PROGRESS: 0,
            UserProgress.Status.COMPLETED: 0,
        }
        for row in counts:
            summary[row["status"]] = row["count"]
        return summary


class UserSavedItemsQueryset:
    """
    All DB query logic for the UserSavedItems model.
    """

    @staticmethod
    def get_saved_courses_for_user(user_id) -> QuerySet:
        """
        Return all saved courses for a user, with course pre-fetched.
        """
        return (
            UserSavedItems.objects.filter(
                user_id=user_id, item_type=UserSavedItems.ItemType.COURSE
            )
            .select_related("course")
            .order_by("-created_at")
        )

    @staticmethod
    def get_saved_combos_for_user(user_id) -> QuerySet:
        """
        Return all saved combos for a user, with combo pre-fetched.
        """
        return (
            UserSavedItems.objects.filter(
                user_id=user_id, item_type=UserSavedItems.ItemType.COMBO
            )
            .select_related("combo")
            .order_by("-created_at")
        )

    @staticmethod
    def get_saved_course(user_id, course_id) -> UserSavedItems | None:
        """Check if a user has saved a specific course. Returns the record or None."""
        try:
            return UserSavedItems.objects.get(
                user_id=user_id,
                course_id=course_id,
                item_type=UserSavedItems.ItemType.COURSE,
            )
        except UserSavedItems.DoesNotExist:
            return None

    @staticmethod
    def get_saved_combo(user_id, combo_id) -> UserSavedItems | None:
        """Check if a user has saved a specific combo. Returns the record or None."""
        try:
            return UserSavedItems.objects.get(
                user_id=user_id,
                combo_id=combo_id,
                item_type=UserSavedItems.ItemType.COMBO,
            )
        except UserSavedItems.DoesNotExist:
            return None

    @staticmethod
    def get_saved_course_ids_for_user(user_id) -> set:
        """Return a set of course IDs saved by a user. Used for bulk status checks."""
        return set(
            UserSavedItems.objects.filter(
                user_id=user_id, item_type=UserSavedItems.ItemType.COURSE
            ).values_list("course_id", flat=True)
        )

    @staticmethod
    def get_saved_combo_ids_for_user(user_id) -> set:
        """Return a set of combo IDs saved by a user. Used for bulk status checks."""
        return set(
            UserSavedItems.objects.filter(
                user_id=user_id, item_type=UserSavedItems.ItemType.COMBO
            ).values_list("combo_id", flat=True)
        )