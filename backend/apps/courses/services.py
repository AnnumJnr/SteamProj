"""
Course services.

All business logic for the Course model lives here.
Views call services. Services call querysets.

Rules enforced:
- Rule 1: Single source of truth for logic
- Rule 3: Services are the entry point for business logic
- Rule 5: Business validation lives here
- Rule 15: No direct model writes outside services
"""

import logging

from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet

from apps.courses.models import Course
from apps.courses.querysets import CourseQueryset
from apps.progress.querysets import UserProgressQueryset

logger = logging.getLogger(__name__)


class CourseService:
    """
    Business logic for course access, filtering, and search.

    Note: Course creation and updates happen exclusively through the ingestion
    pipeline (apps/ingestion/). The only write operation here is deactivation.
    """

    @staticmethod
    def get_course_list(
        category: str = None,
        level: str = None,
        age_group: str = None,
        provider: str = None,
        format: str = None,
        search: str = None,
    ) -> QuerySet:
        """
        Return a filtered, searchable queryset of active courses.
        All filter parameters are optional — unset filters are ignored.

        Called by: CourseListView
        """
        return CourseQueryset.apply_filters(
            category=category,
            level=level,
            age_group=age_group,
            provider=provider,
            format=format,
            search=search,
        )

    @staticmethod
    def get_course_detail(course_id) -> Course | None:
        """
        Return a single active course by ID.
        Returns None if not found or inactive.

        Called by: CourseDetailView
        """
        course = CourseQueryset.get_by_id(course_id)
        if course is None:
            logger.warning(
                "CourseService.get_course_detail: Course not found or inactive: %s",
                course_id,
            )
        return course

    @staticmethod
    def get_courses_for_combo(combo_id) -> QuerySet:
        """
        Return courses belonging to a combo, ordered by position.
        Called by: ComboDetailView when serializing course list.
        """
        return CourseQueryset.get_by_combo(combo_id)

    @staticmethod
    def get_unlocked_course_ids(user) -> set:
        """
        Return the set of course IDs a user may watch (video gate unlocked).

        Gate rule: the user is authenticated AND has an active non-unenrolled
        progress record for the course (in_progress or completed). Anonymous
        users get an empty set — every YouTube course is locked.

        MULTI-USE: Used by courses, progress, and combos views to prime
        serializer context. Changes here affect all of those endpoints.
        """
        if isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
            return set()
        return UserProgressQueryset.get_started_course_ids_for_user(user.pk)

    @staticmethod
    def access_context(user) -> dict:
        """
        Build the serializer context key that carries the video gate.

        Serializers receive this via context["unlocked_course_ids"]; a missing
        key is treated as "nothing unlocked", so every view that renders
        course data MUST call this and merge it into the serializer context.

        Called by: all views that serialize courses (courses/, progress/, combos/).
        """
        return {"unlocked_course_ids": CourseService.get_unlocked_course_ids(user)}

    @staticmethod
    def get_course_videos(course: Course) -> QuerySet:
        """
        Return the stored playlist videos of a course, in playlist order.

        Called by: CourseDetailSerializer — must only be called when the
        video gate is unlocked (view/service responsibility, Rule 15).
        """
        return course.video_items.all()

    @staticmethod
    def deactivate_course(course: Course) -> Course:
        """
        Deactivate a course — hides it from public listings but retains DB record.
        Used by admin actions. Preferred over deletion to preserve ingestion history.
        """
        course.is_active = False
        course.save(update_fields=["is_active", "updated_at"])
        logger.info(
            "CourseService.deactivate_course: Course deactivated: %s (%s)",
            course.title,
            course.pk,
        )
        return course