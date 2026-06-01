"""
Course serializers.

Format and type validation only. No business logic.
Business rules live in courses/services.py.

Rule 5: Serializers handle format and type validation only.
Rule 10: Frontend TypeScript types must match serializer output exactly.
"""

from rest_framework import serializers

from apps.courses.models import Course


class CourseListSerializer(serializers.ModelSerializer):
    """
    Compact course representation for list views and combo course listings.
    Only includes fields needed for a course card.

    Output shape (must match frontend types/course.ts → CourseListItem exactly):
    {
      id, title, short_description, provider, provider_type, source_url,
      category, sub_category, level, age_group, format,
      duration_hours, duration_minutes, thumbnail_url,
      is_free, rating_average, rating_count, tags
    }
    """

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "short_description",
            "provider",
            "provider_type",
            "source_url",
            "category",
            "sub_category",
            "level",
            "age_group",
            "format",
            "duration_hours",
            "duration_minutes",
            "thumbnail_url",
            "is_free",
            "rating_average",
            "rating_count",
            "tags",
        ]
        read_only_fields = fields


class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Full course representation for the detail view.
    Includes all fields needed for the course detail page and the embed player.

    Output shape (must match frontend types/course.ts → CourseDetail exactly):
    All CourseListItem fields + full_description, learning_outcomes,
    prerequisites, instructor, language, certificate_available, is_active
    """

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "short_description",
            "full_description",
            "learning_outcomes",
            "prerequisites",
            "provider",
            "provider_type",
            "source_url",
            "instructor",
            "category",
            "sub_category",
            "tags",
            "level",
            "age_group",
            "language",
            "format",
            "duration_hours",
            "duration_minutes",
            "thumbnail_url",
            "is_free",
            "certificate_available",
            "rating_average",
            "rating_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields