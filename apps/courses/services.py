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

from django.db.models import QuerySet

from apps.courses.models import Course
from apps.courses.querysets import CourseQueryset

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