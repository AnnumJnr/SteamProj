"""
Combo querysets.

All database query logic for Combo, ComboCourse, and ComboRating lives here.
Views and services must never construct raw ORM queries outside this file.

Rule 4: Query logic must be centralized.
"""

import logging

from django.db.models import Avg, Count, QuerySet

from apps.combos.models import Combo, ComboCourse, ComboRating

logger = logging.getLogger(__name__)


class ComboQueryset:
    """
    All DB query logic for the Combo model.
    """

    @staticmethod
    def get_public() -> QuerySet:
        """
        Return all public combos with course count and average rating annotated.
        Used for public combo listings.
        """
        return (
            Combo.objects.filter(is_public=True)
            .annotate(
                course_count=Count("combo_courses", distinct=True),
                average_rating=Avg("ratings__rating"),
                rating_count=Count("ratings", distinct=True),
            )
            .order_by("-is_featured", "-created_at")
        )

    @staticmethod
    def get_featured() -> QuerySet:
        """Return featured public combos only."""
        return ComboQueryset.get_public().filter(is_featured=True)

    @staticmethod
    def get_by_id_public(combo_id) -> Combo | None:
        """
        Return a public combo by primary key, or None.
        Used for unauthenticated detail views.
        """
        try:
            return (
                Combo.objects.filter(pk=combo_id, is_public=True)
                .annotate(
                    course_count=Count("combo_courses", distinct=True),
                    average_rating=Avg("ratings__rating"),
                    rating_count=Count("ratings", distinct=True),
                )
                .get()
            )
        except Combo.DoesNotExist:
            return None

    @staticmethod
    def get_by_id(combo_id) -> Combo | None:
        """
        Return a combo by primary key regardless of visibility.
        Used for owner/admin access.
        """
        try:
            return (
                Combo.objects.filter(pk=combo_id)
                .annotate(
                    course_count=Count("combo_courses", distinct=True),
                    average_rating=Avg("ratings__rating"),
                    rating_count=Count("ratings", distinct=True),
                )
                .get()
            )
        except Combo.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user_id) -> QuerySet:
        """
        Return all combos created by a specific user (public and private).
        Used in user dashboard and combo management.
        """
        return (
            Combo.objects.filter(created_by_user_id=user_id)
            .annotate(
                course_count=Count("combo_courses", distinct=True),
                average_rating=Avg("ratings__rating"),
                rating_count=Count("ratings", distinct=True),
            )
            .order_by("-created_at")
        )

    @staticmethod
    def filter_by_category(queryset: QuerySet, category: str) -> QuerySet:
        """Filter combos by STEM category."""
        return queryset.filter(category=category)

    @staticmethod
    def filter_by_difficulty(queryset: QuerySet, difficulty: str) -> QuerySet:
        """Filter combos by difficulty level."""
        return queryset.filter(difficulty=difficulty)

    @staticmethod
    def filter_by_age(queryset: QuerySet, recommended_age: str) -> QuerySet:
        """Filter combos by recommended age group."""
        return queryset.filter(recommended_age=recommended_age)

    @staticmethod
    def search(queryset: QuerySet, query: str) -> QuerySet:
        """Keyword search on combo titles (icontains). Elasticsearch deferred to Phase 3)."""
        if not query:
            return queryset
        return queryset.filter(title__icontains=query)

    @staticmethod
    def apply_filters(
        category: str = None,
        difficulty: str = None,
        recommended_age: str = None,
        search: str = None,
    ) -> QuerySet:
        """
        Entry point for all public combo listing queries from the API.
        Chains filters on top of the public base queryset.
        """
        qs = ComboQueryset.get_public()

        if category:
            qs = ComboQueryset.filter_by_category(qs, category)
        if difficulty:
            qs = ComboQueryset.filter_by_difficulty(qs, difficulty)
        if recommended_age:
            qs = ComboQueryset.filter_by_age(qs, recommended_age)
        if search:
            qs = ComboQueryset.search(qs, search)

        return qs


class ComboCourseQueryset:
    """
    All DB query logic for the ComboCourse junction table.
    """

    @staticmethod
    def get_by_combo(combo_id) -> QuerySet:
        """Return all ComboCourse entries for a combo, ordered by position."""
        return (
            ComboCourse.objects.filter(combo_id=combo_id)
            .select_related("course")
            .order_by("order")
        )

    @staticmethod
    def get_max_order(combo_id) -> int:
        """
        Return the current highest order value for a combo.
        Used when appending a new course to a combo.
        Returns 0 if the combo has no courses yet.
        """
        result = ComboCourse.objects.filter(combo_id=combo_id).aggregate(
            max_order=Count("order")
        )
        return result["max_order"] or 0

    @staticmethod
    def get_by_combo_and_course(combo_id, course_id) -> ComboCourse | None:
        """Return a specific ComboCourse entry, or None if not found."""
        try:
            return ComboCourse.objects.get(combo_id=combo_id, course_id=course_id)
        except ComboCourse.DoesNotExist:
            return None


class ComboRatingQueryset:
    """
    All DB query logic for the ComboRating model.
    """

    @staticmethod
    def get_by_combo_and_user(combo_id, user_id) -> ComboRating | None:
        """Return a user's rating for a specific combo, or None."""
        try:
            return ComboRating.objects.get(combo_id=combo_id, user_id=user_id)
        except ComboRating.DoesNotExist:
            return None

    @staticmethod
    def get_ratings_for_combo(combo_id) -> QuerySet:
        """Return all ratings for a combo, newest first."""
        return (
            ComboRating.objects.filter(combo_id=combo_id)
            .select_related("user")
            .order_by("-created_at")
        )