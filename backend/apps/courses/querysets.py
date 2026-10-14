"""
Course querysets.

All database query logic for the Course model lives here.
This includes filtering, search, and ordering — never in views or services.

Changes from Phase 2:
- get_active() now also filters on language_status.
  Courses with language_status=rejected are excluded from all public listings.
  Courses with language_status=unknown or accepted remain visible.
  Courses with language_status=flagged remain visible (human review pending —
  we do not hide them automatically because the detection may be wrong).

Rule 4: Query logic must be centralized.
"""

import logging

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import QuerySet

from apps.courses.models import Course

logger = logging.getLogger(__name__)

# Statuses that are visible in the public catalog.
# UNKNOWN and ACCEPTED are visible. FLAGGED is visible (pending human review).
# REJECTED is excluded — confident non-English, hidden from catalog.
PUBLIC_LANGUAGE_STATUSES = [
    Course.LanguageStatus.UNKNOWN,
    Course.LanguageStatus.ACCEPTED,
    Course.LanguageStatus.FLAGGED,
]


class CourseQueryset:
    """
    All DB query logic for the Course model.
    """

    @staticmethod
    def get_active() -> QuerySet:
        """
        Return all active, language-eligible courses ordered by title.

        Excludes:
          - is_active=False   (course gone from source platform)
          - language_status=rejected (confident non-English)

        Does NOT exclude language_status=flagged — flagged courses are
        still visible while awaiting human review. This is intentional:
        the detection pipeline may produce false positives, and we do not
        want to silently hide potentially valid English courses from users
        before a human has confirmed the rejection.
        """
        return Course.objects.filter(
            is_active=True,
            language_status__in=PUBLIC_LANGUAGE_STATUSES,
        ).order_by("title")

    @staticmethod
    def get_by_id(course_id) -> Course | None:
        """Return an active, language-eligible course by primary key, or None."""
        try:
            return Course.objects.get(
                pk=course_id,
                is_active=True,
                language_status__in=PUBLIC_LANGUAGE_STATUSES,
            )
        except Course.DoesNotExist:
            return None

    @staticmethod
    def get_by_id_any_status(course_id) -> Course | None:
        """
        Return a course by primary key regardless of active or language status.
        Used in admin and ingestion contexts only — not for public-facing queries.
        """
        try:
            return Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return None

    @staticmethod
    def filter_by_category(queryset: QuerySet, category: str) -> QuerySet:
        """Filter courses by top-level STEM category."""
        return queryset.filter(category=category)

    @staticmethod
    def filter_by_level(queryset: QuerySet, level: str) -> QuerySet:
        """Filter courses by difficulty level (Beginner / Intermediate / Advanced)."""
        return queryset.filter(level=level)

    @staticmethod
    def filter_by_age_group(queryset: QuerySet, age_group: str) -> QuerySet:
        """Filter courses by target age group (Kids / Teens / Adults)."""
        return queryset.filter(age_group=age_group)

    @staticmethod
    def filter_by_provider(queryset: QuerySet, provider: str) -> QuerySet:
        """Filter courses by source provider."""
        return queryset.filter(provider=provider)

    @staticmethod
    def filter_by_format(queryset: QuerySet, format: str) -> QuerySet:
        """Filter courses by content format (Video / Text / Interactive)."""
        return queryset.filter(format=format)

    @staticmethod
    def search(queryset: QuerySet, query: str) -> QuerySet:
        """
        Full-text search across course title and tags using PostgreSQL tsvector.

        Falls back to icontains on title if the search_vector field is not yet
        populated (e.g. freshly ingested courses before the vector update runs).

        FALLBACK: icontains title search
        PRIMARY: apps/courses/querysets.py → CourseQueryset.search()
        CONDITION: search_vector is null or not yet populated
        THRESHOLD: Not applicable — silent degradation is acceptable for search
        """
        if not query:
            return queryset

        search_query = SearchQuery(query, search_type="websearch")
        qs_fts = queryset.filter(search_vector=search_query).annotate(
            rank=SearchRank("search_vector", search_query)
        ).order_by("-rank")

        if qs_fts.exists():
            return qs_fts

        # FALLBACK: icontains on title if search_vector not yet populated
        # PRIMARY: apps/courses/querysets.py → CourseQueryset.search()
        # CONDITION: search_vector is null or FTS returns no results
        # THRESHOLD: Not applicable — icontains is an acceptable search degradation
        logger.warning(
            "CourseQueryset.search: FTS returned no results for '%s'. "
            "Falling back to title icontains. Check search_vector population.",
            query,
        )
        return queryset.filter(title__icontains=query)

    @staticmethod
    def apply_filters(
        category: str = None,
        level: str = None,
        age_group: str = None,
        provider: str = None,
        format: str = None,
        search: str = None,
    ) -> QuerySet:
        """
        Entry point for all course listing/search queries from the API.
        Chains filters and search on top of the active base queryset.
        language_status filtering is applied at the get_active() level.

        MULTI-USE: Used by CourseListView and combo course pickers.
        """
        qs = CourseQueryset.get_active()

        if category:
            qs = CourseQueryset.filter_by_category(qs, category)
        if level:
            qs = CourseQueryset.filter_by_level(qs, level)
        if age_group:
            qs = CourseQueryset.filter_by_age_group(qs, age_group)
        if provider:
            qs = CourseQueryset.filter_by_provider(qs, provider)
        if format:
            qs = CourseQueryset.filter_by_format(qs, format)
        if search:
            qs = CourseQueryset.search(qs, search)

        return qs

    @staticmethod
    def get_by_combo(combo_id) -> QuerySet:
        """
        Return courses belonging to a specific combo, ordered by their position.
        Only returns active, language-eligible courses.
        """
        return (
            Course.objects.filter(
                combo_courses__combo_id=combo_id,
                is_active=True,
                language_status__in=PUBLIC_LANGUAGE_STATUSES,
            )
            .order_by("combo_courses__order")
            .select_related()
        )