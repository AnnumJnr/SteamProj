"""
Combo serializers.

Format and type validation only. No business logic.
Business rules live in combos/services.py.

Rule 5: Serializers handle format and type validation only.
Rule 10: Frontend TypeScript types must match serializer output exactly.
"""

from rest_framework import serializers

from apps.combos.models import Combo, ComboCourse, ComboRating
from apps.courses.serializers import CourseListSerializer


class ComboCourseSerializer(serializers.ModelSerializer):
    """
    Represents a single course entry within a combo, including its order and metadata.
    Nests the full CourseListSerializer for course card data.
    """

    course = CourseListSerializer(read_only=True)

    class Meta:
        model = ComboCourse
        fields = ["order", "is_required", "note", "course"]
        read_only_fields = fields


class ComboListSerializer(serializers.ModelSerializer):
    """
    Compact combo representation for list views.
    Includes annotated fields from ComboQueryset (course_count, average_rating, rating_count).

    Output shape (must match frontend types/combo.ts → ComboListItem exactly):
    {
      id, title, short_description, category, sub_category, difficulty,
      recommended_age, estimated_weeks, estimated_hours_per_week,
      is_public, is_featured, tags, created_by_type,
      course_count, average_rating, rating_count, created_at
    }
    """

    # Annotated fields from queryset
    course_count = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    rating_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Combo
        fields = [
            "id",
            "title",
            "short_description",
            "category",
            "sub_category",
            "difficulty",
            "recommended_age",
            "estimated_weeks",
            "estimated_hours_per_week",
            "is_public",
            "is_featured",
            "tags",
            "created_by_type",
            "course_count",
            "average_rating",
            "rating_count",
            "created_at",
        ]
        read_only_fields = fields


class ComboDetailSerializer(serializers.ModelSerializer):
    """
    Full combo representation for the detail view.
    Includes nested ordered courses and all metadata.

    Output shape (must match frontend types/combo.ts → ComboDetail exactly):
    All ComboListItem fields + full_description, overview, who_is_this_for,
    learning_outcomes, prerequisites, skills_gained, learning_path_explanation,
    courses (nested ordered list), updated_at
    """

    courses = ComboCourseSerializer(source="combo_courses", many=True, read_only=True)
    course_count = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    rating_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Combo
        fields = [
            "id",
            "title",
            "short_description",
            "full_description",
            "overview",
            "who_is_this_for",
            "learning_outcomes",
            "prerequisites",
            "skills_gained",
            "learning_path_explanation",
            "category",
            "sub_category",
            "difficulty",
            "recommended_age",
            "estimated_weeks",
            "estimated_hours_per_week",
            "is_public",
            "is_featured",
            "tags",
            "created_by_type",
            "courses",
            "course_count",
            "average_rating",
            "rating_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CreateComboCourseInputSerializer(serializers.Serializer):
    """Validates individual course input within a combo creation payload."""
    course_id = serializers.UUIDField()
    is_required = serializers.BooleanField(default=True, required=False)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    # Note: order is determined by array position, not sent from frontend


class CreateComboSerializer(serializers.Serializer):
    """
    Validates combo creation input (POST /combos/).
    Business logic lives in ComboService.create_combo().

    course_ids is optional — users can create a combo shell and add courses later.
    """

    title = serializers.CharField(max_length=300)
    short_description = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    full_description = serializers.CharField(required=False, allow_blank=True, default="")
    overview = serializers.CharField(required=False, allow_blank=True, default="")
    who_is_this_for = serializers.CharField(required=False, allow_blank=True, default="")
    learning_outcomes = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    prerequisites = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    skills_gained = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    learning_path_explanation = serializers.CharField(required=False, allow_blank=True, default="")
    category = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    sub_category = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    difficulty = serializers.ChoiceField(
        choices=Combo.Difficulty.choices, required=False, default=Combo.Difficulty.BEGINNER
    )
    recommended_age = serializers.ChoiceField(
        choices=Combo.RecommendedAge.choices, required=False, default=Combo.RecommendedAge.ALL_AGES
    )
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    estimated_weeks = serializers.IntegerField(min_value=0, required=False, default=0)
    estimated_hours_per_week = serializers.IntegerField(min_value=0, required=False, default=0)
    courses = serializers.ListField(
        child=CreateComboCourseInputSerializer(),
        required=False,
        default=list
    )


class UpdateComboCourseInputSerializer(serializers.Serializer):
    """Validates individual course input within a combo update payload."""
    course_id = serializers.UUIDField()
    is_required = serializers.BooleanField(required=False)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class UpdateComboSerializer(serializers.Serializer):
    """
    Validates combo update input (PATCH /combos/{id}/).
    All fields optional — only provided fields are updated.
    Business logic lives in ComboService.update_combo().
    """

    title = serializers.CharField(max_length=300, required=False)
    short_description = serializers.CharField(max_length=300, required=False, allow_blank=True)
    full_description = serializers.CharField(required=False, allow_blank=True)
    overview = serializers.CharField(required=False, allow_blank=True)
    who_is_this_for = serializers.CharField(required=False, allow_blank=True)
    learning_outcomes = serializers.ListField(child=serializers.CharField(), required=False)
    prerequisites = serializers.ListField(child=serializers.CharField(), required=False)
    skills_gained = serializers.ListField(child=serializers.CharField(), required=False)
    learning_path_explanation = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(max_length=50, required=False, allow_blank=True)
    sub_category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    difficulty = serializers.ChoiceField(choices=Combo.Difficulty.choices, required=False)
    recommended_age = serializers.ChoiceField(choices=Combo.RecommendedAge.choices, required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    estimated_weeks = serializers.IntegerField(min_value=0, required=False)
    estimated_hours_per_week = serializers.IntegerField(min_value=0, required=False)
    is_public = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)  # Silently ignored for non-staff — service enforces
    courses = serializers.ListField(
    child=UpdateComboCourseInputSerializer(), required=False
    )

class ComboRatingSerializer(serializers.ModelSerializer):
    """
    Read serializer for combo ratings.
    Used when listing ratings for a combo.
    """

    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ComboRating
        fields = ["id", "user_email", "rating", "review", "created_at"]
        read_only_fields = fields


class CreateComboRatingSerializer(serializers.Serializer):
    """
    Validates combo rating input (POST /combos/{id}/rate/).
    Business logic lives in ComboRatingService.rate_combo().
    """

    rating = serializers.IntegerField(min_value=1, max_value=5)
    review = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")