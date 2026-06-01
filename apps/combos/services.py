"""
Combo services.

All business logic for Combo, ComboCourse, and ComboRating lives here.
Views call services. Services call querysets.

Rules enforced:
- Rule 1: Single source of truth for logic
- Rule 3: Services are the entry point for business logic
- Rule 5: Business validation lives here
- Rule 9: No hidden side effects
- Rule 15: No direct model writes outside services
"""

import logging

from django.db import transaction
from django.db.models import QuerySet

from apps.combos.models import Combo, ComboCourse, ComboRating
from apps.combos.querysets import ComboCourseQueryset, ComboQueryset, ComboRatingQueryset
from apps.courses.querysets import CourseQueryset
from apps.progress.querysets import UserProgressQueryset
from apps.users.models import User

logger = logging.getLogger(__name__)


class ComboService:
    """
    Business logic for combo access, creation, and management.
    """

    @staticmethod
    def get_combo_list(
        category: str = None,
        difficulty: str = None,
        recommended_age: str = None,
        search: str = None,
    ) -> QuerySet:
        """
        Return a filtered queryset of public combos.
        All filter parameters are optional.
        Called by: ComboListView
        """
        return ComboQueryset.apply_filters(
            category=category,
            difficulty=difficulty,
            recommended_age=recommended_age,
            search=search,
        )

    @staticmethod
    def get_combo_detail(combo_id, user: User = None) -> Combo | None:
        """
        Return a single combo by ID.

        Access rules:
        - Public combos: accessible by anyone (user=None allowed)
        - Private combos: accessible only by their creator or admin

        Returns None if not found or access is denied.
        """
        combo = ComboQueryset.get_by_id(combo_id)
        if combo is None:
            return None

        if combo.is_public:
            return combo

        # Private combo — only owner or admin can view
        if user is None:
            logger.warning(
                "ComboService.get_combo_detail: Unauthenticated access attempt to private combo %s",
                combo_id,
            )
            return None

        if combo.created_by_user_id == user.pk or user.is_staff:
            return combo

        logger.warning(
            "ComboService.get_combo_detail: User %s denied access to private combo %s",
            user.email,
            combo_id,
        )
        return None

    @staticmethod
    def get_user_combos(user_id) -> QuerySet:
        """
        Return all combos created by a user (public and private).
        Called by: user dashboard, combo management views.
        """
        return ComboQueryset.get_by_user(user_id)

    @staticmethod
    @transaction.atomic
    def create_combo(user: User, data: dict) -> Combo:
        """
        Create a new combo for a user.

        Business rules enforced:
        - User-created combos are private by default
        - created_by_type is always 'user' for user-created combos
        - is_featured is always False for user-created combos (admin-only privilege)
        - courses list, if provided, must reference valid active courses
        - Combo must have a title

        Raises:
            ValueError: If title is missing or any course_id is invalid.
        """
        title = data.get("title", "").strip()
        if not title:
            raise ValueError("Combo title is required.")

        # Changed: extract courses instead of course_ids
        courses_data = data.pop("courses", [])

        # Validate all course IDs before writing anything
        for i, course_item in enumerate(courses_data, start=1):
            course_id = course_item.get("course_id")
            if CourseQueryset.get_by_id(course_id) is None:
                raise ValueError(f"Course not found or inactive at position {i}: {course_id}")

        combo = Combo.objects.create(
            created_by_user=user,
            created_by_type=Combo.CreatedBy.USER,
            is_public=False,   # Always private by default — master reference §3
            is_featured=False,  # Users cannot feature their own combos
            **{k: v for k, v in data.items() if k != "is_featured"},
        )

        # Create ComboCourse entries with all fields, order determined by position
        for i, course_item in enumerate(courses_data, start=1):
            course = CourseQueryset.get_by_id(course_item["course_id"])
            ComboCourse.objects.create(
                combo=combo,
                course=course,
                order=i,
                is_required=course_item.get("is_required", True),
                note=course_item.get("note", ""),
            )

        logger.info(
            "ComboService.create_combo: Combo '%s' created by user %s with %d courses",
            combo.title,
            user.email,
            len(courses_data),
        )
        return combo

    @staticmethod
    @transaction.atomic
    def update_combo(combo: Combo, user: User, data: dict) -> Combo:
        """
        Update an existing combo.

        Business rules enforced:
        - Only the owner or an admin can update a combo
        - is_featured cannot be set by users (admin-only)
        - courses, if provided, replaces the entire course list

        Raises:
            PermissionError: If the user is not the owner or admin.
            ValueError: If any course_id in courses is invalid.
        """
        if combo.created_by_user_id != user.pk and not user.is_staff:
            raise PermissionError("You do not have permission to edit this combo.")

        courses_data = data.pop("courses", None)

        # Prevent non-admins from featuring their own combos
        if not user.is_staff and "is_featured" in data:
            data.pop("is_featured")
            logger.warning(
                "ComboService.update_combo: User %s attempted to set is_featured. Ignored.",
                user.email,
            )

        allowed_fields = {
            "title", "short_description", "full_description", "overview",
            "who_is_this_for", "learning_outcomes", "prerequisites", "skills_gained",
            "learning_path_explanation", "category", "sub_category", "difficulty",
            "recommended_age", "tags", "estimated_weeks", "estimated_hours_per_week",
            "is_public",
        }
        if user.is_staff:
            allowed_fields.add("is_featured")

        update_fields = []
        for field, value in data.items():
            if field in allowed_fields:
                setattr(combo, field, value)
                update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            combo.save(update_fields=update_fields)

        # Replace courses if a new list was provided
        if courses_data is not None:
            # Validate all course IDs before modifying anything
            for i, course_item in enumerate(courses_data, start=1):
                course_id = course_item.get("course_id")
                if not course_id:
                    raise ValueError(f"course_id required at position {i}")
                if CourseQueryset.get_by_id(course_id) is None:
                    raise ValueError(f"Course not found or inactive at position {i}: {course_id}")

            # Delete existing course associations
            ComboCourse.objects.filter(combo=combo).delete()

            # Create new course associations with all fields
            for i, course_item in enumerate(courses_data, start=1):
                course = CourseQueryset.get_by_id(course_item["course_id"])
                ComboCourse.objects.create(
                    combo=combo,
                    course=course,
                    order=i,
                    is_required=course_item.get("is_required", True),
                    note=course_item.get("note", ""),
                )
            logger.info(
                "ComboService.update_combo: Combo '%s' course list replaced with %d courses",
                combo.title,
                len(courses_data),
            )

        logger.info(
            "ComboService.update_combo: Combo '%s' updated by user %s",
            combo.title,
            user.email,
        )
        return combo
    
    @staticmethod
    def delete_combo(combo: Combo, user: User) -> None:
        """
        Delete a combo.

        Business rules enforced:
        - Only the owner or an admin can delete a combo

        Raises:
            PermissionError: If the user is not the owner or admin.
        """
        if combo.created_by_user_id != user.pk and not user.is_staff:
            raise PermissionError("You do not have permission to delete this combo.")

        combo_title = combo.title
        combo.delete()
        logger.info(
            "ComboService.delete_combo: Combo '%s' deleted by user %s",
            combo_title,
            user.email,
        )

    @staticmethod
    def remove_course_from_combo(combo: Combo, course_id: str) -> None:
        """
        Remove a single course from a combo and re-sequence remaining courses.
        Raises:
            ValueError: If the course is not in the combo.
        """
        try:
            combo_course = ComboCourse.objects.get(combo=combo, course_id=course_id)
        except ComboCourse.DoesNotExist:
            raise ValueError(f"Course {course_id} not found in this combo.")

        combo_course.delete()

        # Re-sequence remaining courses from 1
        remaining = ComboCourse.objects.filter(combo=combo).order_by("order")
        for idx, cc in enumerate(remaining, start=1):
            if cc.order != idx:
                cc.order = idx
                cc.save(update_fields=["order"])

        logger.info(
            "ComboService.remove_course_from_combo: Removed course %s from combo '%s'",
            course_id,
            combo.title,
        )


    @staticmethod
    def get_combo_progress(combo_id, user_id) -> dict:
        """
        Calculate a user's progress through a combo.

        Returns a dict with:
        - total_courses: int
        - completed_courses: int
        - completion_percentage: float (0.0–100.0)
        - completed_course_ids: list of UUIDs

        MULTI-USE: Called by ComboDetailView and user dashboard.
        """
        combo_course_ids = set(
            ComboCourse.objects.filter(combo_id=combo_id).values_list("course_id", flat=True)
        )
        completed_ids = UserProgressQueryset.get_completed_course_ids_for_user(user_id)
        completed_in_combo = combo_course_ids & completed_ids

        total = len(combo_course_ids)
        completed = len(completed_in_combo)
        percentage = round((completed / total * 100), 1) if total > 0 else 0.0

        return {
            "total_courses": total,
            "completed_courses": completed,
            "completion_percentage": percentage,
            "completed_course_ids": list(completed_in_combo),
        }


class ComboRatingService:
    """
    Business logic for combo ratings.
    """

    @staticmethod
    def rate_combo(combo: Combo, user: User, rating: int, review: str = "") -> ComboRating:
        """
        Create or update a user's rating for a combo.

        Business rules enforced:
        - Rating must be 1–5 (enforced at model level via validators)
        - One rating per user per combo (upsert pattern)
        - Users cannot rate their own combos

        Raises:
            ValueError: If the user tries to rate their own combo.
        """
        if combo.created_by_user_id == user.pk:
            raise ValueError("You cannot rate your own combo.")

        existing = ComboRatingQueryset.get_by_combo_and_user(combo.pk, user.pk)

        if existing:
            existing.rating = rating
            existing.review = review
            existing.save(update_fields=["rating", "review", "updated_at"])
            logger.info(
                "ComboRatingService.rate_combo: User %s updated rating for combo '%s': %d",
                user.email,
                combo.title,
                rating,
            )
            return existing

        combo_rating = ComboRating.objects.create(
            combo=combo,
            user=user,
            rating=rating,
            review=review,
        )
        logger.info(
            "ComboRatingService.rate_combo: User %s rated combo '%s': %d",
            user.email,
            combo.title,
            rating,
        )
        return combo_rating

    @staticmethod
    def delete_rating(combo: Combo, user: User) -> None:
        """
        Delete a user's rating for a combo.

        Raises:
            ValueError: If no rating exists to delete.
        """
        rating = ComboRatingQueryset.get_by_combo_and_user(combo.pk, user.pk)
        if rating is None:
            raise ValueError("No rating found to delete.")

        rating.delete()
        logger.info(
            "ComboRatingService.delete_rating: User %s removed rating for combo '%s'",
            user.email,
            combo.title,
        )


'''@staticmethod
    def remove_course_from_combo(combo: Combo, course_id: str) -> None:
        """
        Remove a single course from a combo.
        Re-orders remaining courses to maintain sequential order.
        
        Raises:
            ValueError: If course is not in the combo.
        """
        try:
            combo_course = ComboCourse.objects.get(combo=combo, course_id=course_id)
        except ComboCourse.DoesNotExist:
            raise ValueError(f"Course {course_id} not found in this combo.")

        # Delete the course
        combo_course.delete()
        
        # Re-order remaining courses
        remaining = ComboCourse.objects.filter(combo=combo).order_by("order")
        for idx, cc in enumerate(remaining, start=1):
            if cc.order != idx:
                cc.order = idx
                cc.save(update_fields=["order"])
        
        logger.info(
            "ComboService.remove_course_from_combo: Removed course %s from combo '%s'",
            course_id,
            combo.title,
        )
        '''
