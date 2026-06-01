"""
Progress services.

All business logic for UserProgress and UserSavedItems lives here.
Views call services. Services call querysets.

Rules enforced:
- Rule 1: Single source of truth for logic
- Rule 3: Services are the entry point for business logic
- Rule 5: Business validation lives here
- Rule 9: No hidden side effects
- Rule 15: No direct model writes outside services
"""

import logging

from django.utils import timezone

from apps.combos.querysets import ComboQueryset
from apps.courses.querysets import CourseQueryset
from apps.progress.models import UserProgress, UserSavedItems
from apps.progress.querysets import UserProgressQueryset, UserSavedItemsQueryset
from apps.users.models import User

logger = logging.getLogger(__name__)


class UserProgressService:
    """
    Business logic for self-reported course progress.

    Master reference §3: Progress is self-reported. User clicks "Mark as Complete".
    Platform does not verify actual viewing.
    """

    @staticmethod
    def get_user_progress(user_id):
        """Return all progress records for a user."""
        return UserProgressQueryset.get_by_user(user_id)

    @staticmethod
    def get_progress_summary(user_id) -> dict:
        """Return aggregate progress counts for the dashboard overview."""
        return UserProgressQueryset.get_summary_for_user(user_id)

    @staticmethod
    def mark_course_started(user: User, course_id) -> UserProgress:
        """
        Mark a course as in-progress for a user.
        Creates the progress record if it does not exist.
        Does nothing if the course is already completed (no regression allowed).

        Business rules:
        - Course must exist and be active
        - Status cannot go backwards (completed → in_progress is rejected)

        Raises:
            ValueError: If the course does not exist or is inactive.
        """
        course = CourseQueryset.get_by_id(course_id)
        if course is None:
            raise ValueError(f"Course not found or inactive: {course_id}")

        existing = UserProgressQueryset.get_by_user_and_course(user.pk, course_id)

        if existing:
            if existing.status == UserProgress.Status.COMPLETED:
                # No regression from completed — return as-is
                logger.info(
                    "UserProgressService.mark_course_started: User %s already completed course %s. No change.",
                    user.email,
                    course_id,
                )
                return existing

            if existing.status == UserProgress.Status.IN_PROGRESS:
                return existing  # Already in progress — idempotent

            existing.status = UserProgress.Status.IN_PROGRESS
            existing.save(update_fields=["status", "updated_at"])
            return existing

        progress = UserProgress.objects.create(
            user=user,
            course=course,
            status=UserProgress.Status.IN_PROGRESS,
        )
        logger.info(
            "UserProgressService.mark_course_started: User %s started course '%s'",
            user.email,
            course.title,
        )
        return progress

    @staticmethod
    def mark_course_complete(user: User, course_id) -> UserProgress:
        """
        Mark a course as completed for a user (self-reported).
        Creates the progress record if it does not exist.
        Sets completed_at timestamp.

        Business rules:
        - Course must exist and be active
        - If already completed, returns the existing record (idempotent)

        Raises:
            ValueError: If the course does not exist or is inactive.
        """
        course = CourseQueryset.get_by_id(course_id)
        if course is None:
            raise ValueError(f"Course not found or inactive: {course_id}")

        existing = UserProgressQueryset.get_by_user_and_course(user.pk, course_id)

        if existing:
            if existing.status == UserProgress.Status.COMPLETED:
                return existing  # Already complete — idempotent

            existing.status = UserProgress.Status.COMPLETED
            existing.completed_at = timezone.now()
            existing.save(update_fields=["status", "completed_at", "updated_at"])
            logger.info(
                "UserProgressService.mark_course_complete: User %s completed course '%s'",
                user.email,
                course.title,
            )
            return existing

        progress = UserProgress.objects.create(
            user=user,
            course=course,
            status=UserProgress.Status.COMPLETED,
            completed_at=timezone.now(),
        )
        logger.info(
            "UserProgressService.mark_course_complete: User %s marked course '%s' complete (new record)",
            user.email,
            course.title,
        )
        return progress

    @staticmethod
    def get_course_progress(user_id, course_id) -> UserProgress | None:
        """Return a user's progress record for a specific course, or None."""
        return UserProgressQueryset.get_by_user_and_course(user_id, course_id)
    
    @staticmethod
    def delete_course_progress(user: User, course_id) -> None:
        """
        Delete all progress for a user on a specific course (unenroll).
        Silently succeeds if no record exists — idempotent.
        """
        existing = UserProgressQueryset.get_by_user_and_course(user.pk, course_id)
        if existing:
            existing.delete()
            logger.info(
                "UserProgressService.delete_course_progress: User %s unenrolled from course %s",
                user.email, course_id,
            )


class UserSavedItemsService:
    """
    Business logic for saving and unsaving courses and combos.
    """

    @staticmethod
    def get_saved_courses(user_id):
        """Return all saved courses for a user."""
        return UserSavedItemsQueryset.get_saved_courses_for_user(user_id)

    @staticmethod
    def get_saved_combos(user_id):
        """Return all saved combos for a user."""
        return UserSavedItemsQueryset.get_saved_combos_for_user(user_id)

    @staticmethod
    def save_course(user: User, course_id) -> UserSavedItems:
        """
        Save a course for a user.
        Idempotent — if already saved, returns existing record.

        Business rules:
        - Course must exist and be active

        Raises:
            ValueError: If the course does not exist or is inactive.
        """
        course = CourseQueryset.get_by_id(course_id)
        if course is None:
            raise ValueError(f"Course not found or inactive: {course_id}")

        existing = UserSavedItemsQueryset.get_saved_course(user.pk, course_id)
        if existing:
            return existing  # Already saved — idempotent

        saved = UserSavedItems.objects.create(
            user=user,
            item_type=UserSavedItems.ItemType.COURSE,
            course=course,
        )
        logger.info(
            "UserSavedItemsService.save_course: User %s saved course '%s'",
            user.email,
            course.title,
        )
        return saved

    @staticmethod
    def unsave_course(user: User, course_id) -> None:
        """
        Remove a saved course for a user.

        Raises:
            ValueError: If the course is not in the user's saved items.
        """
        existing = UserSavedItemsQueryset.get_saved_course(user.pk, course_id)
        if existing is None:
            raise ValueError("This course is not in your saved items.")

        existing.delete()
        logger.info(
            "UserSavedItemsService.unsave_course: User %s unsaved course %s",
            user.email,
            course_id,
        )

    @staticmethod
    def save_combo(user: User, combo_id) -> UserSavedItems:
        """
        Save a combo for a user.
        Idempotent — if already saved, returns existing record.

        Business rules:
        - Combo must exist and be public (users can only save public combos),
          OR the user must be the combo's owner

        Raises:
            ValueError: If the combo is not found or access is denied.
        """
        combo = ComboQueryset.get_by_id(combo_id)
        if combo is None:
            raise ValueError(f"Combo not found: {combo_id}")

        if not combo.is_public and combo.created_by_user_id != user.pk:
            raise ValueError("You do not have access to this combo.")

        existing = UserSavedItemsQueryset.get_saved_combo(user.pk, combo_id)
        if existing:
            return existing  # Already saved — idempotent

        saved = UserSavedItems.objects.create(
            user=user,
            item_type=UserSavedItems.ItemType.COMBO,
            combo=combo,
        )
        logger.info(
            "UserSavedItemsService.save_combo: User %s saved combo '%s'",
            user.email,
            combo.title,
        )
        return saved

    @staticmethod
    def unsave_combo(user: User, combo_id) -> None:
        """
        Remove a saved combo for a user.

        Raises:
            ValueError: If the combo is not in the user's saved items.
        """
        existing = UserSavedItemsQueryset.get_saved_combo(user.pk, combo_id)
        if existing is None:
            raise ValueError("This combo is not in your saved items.")

        existing.delete()
        logger.info(
            "UserSavedItemsService.unsave_combo: User %s unsaved combo %s",
            user.email,
            combo_id,
        )