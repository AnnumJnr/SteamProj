"""
Progress serializers.

Format and type validation only. No business logic.
Business rules live in progress/services.py.

Rule 5: Serializers handle format and type validation only.
Rule 10: Frontend TypeScript types must match serializer output exactly.
"""

from rest_framework import serializers

from apps.combos.serializers import ComboListSerializer
from apps.courses.serializers import CourseListSerializer
from apps.progress.models import UserProgress, UserSavedItems


class UserProgressSerializer(serializers.ModelSerializer):
    """
    Represents a user's progress record for a single course.
    Includes nested course card data for display.

    Output shape (must match frontend types/progress.ts → UserProgress exactly):
    { id, status, completed_at, created_at, updated_at, course: CourseListItem }
    """

    course = CourseListSerializer(read_only=True)

    class Meta:
        model = UserProgress
        fields = ["id", "status", "completed_at", "created_at", "updated_at", "course"]
        read_only_fields = fields


class ProgressSummarySerializer(serializers.Serializer):
    """
    Aggregate progress summary for the dashboard.
    Output from UserProgressQueryset.get_summary_for_user().
    """

    not_started = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()


class MarkCourseActionSerializer(serializers.Serializer):
    """
    Validates the course ID for mark-started / mark-complete actions.
    Used by: POST /progress/start/, POST /progress/complete/
    """

    course_id = serializers.UUIDField()


class ComboProgressSerializer(serializers.Serializer):
    """
    Represents a user's progress through a specific combo.
    Output from ComboService.get_combo_progress().

    Output shape (must match frontend types/progress.ts → ComboProgress exactly):
    { total_courses, completed_courses, completion_percentage, completed_course_ids }
    """

    total_courses = serializers.IntegerField()
    completed_courses = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    completed_course_ids = serializers.ListField(child=serializers.UUIDField())


class SavedCourseSerializer(serializers.ModelSerializer):
    """
    Represents a saved course entry.
    Includes nested course card data.

    Output shape (must match frontend types/progress.ts → SavedCourse exactly):
    { id, item_type, created_at, course: CourseListItem }
    """

    course = CourseListSerializer(read_only=True)

    class Meta:
        model = UserSavedItems
        fields = ["id", "item_type", "created_at", "course"]
        read_only_fields = fields


class SavedComboSerializer(serializers.ModelSerializer):
    """
    Represents a saved combo entry.
    Includes nested combo card data.

    Output shape (must match frontend types/progress.ts → SavedCombo exactly):
    { id, item_type, created_at, combo: ComboListItem }
    """

    combo = ComboListSerializer(read_only=True)

    class Meta:
        model = UserSavedItems
        fields = ["id", "item_type", "created_at", "combo"]
        read_only_fields = fields


class SaveItemSerializer(serializers.Serializer):
    """
    Validates input for save/unsave actions.
    Used by: POST /progress/saved/courses/, DELETE /progress/saved/courses/{id}/
    Used by: POST /progress/saved/combos/, DELETE /progress/saved/combos/{id}/
    """

    item_id = serializers.UUIDField()