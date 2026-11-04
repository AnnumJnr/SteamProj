"""
Course serializers.

Format and type validation only. No business logic.
Business rules live in courses/services.py.

Rule 5: Serializers handle format and type validation only.
Rule 10: Frontend TypeScript types must match serializer output exactly.
"""

from rest_framework import serializers

from apps.courses.models import Course, CourseVideoItem


class VideoGateMixin:
    """
    Adds video-gate behaviour to course serializers.

    The gate is decided by services (CourseService.access_context) and passed
    in through context["unlocked_course_ids"] — a set of course IDs the
    requesting user may watch. Views that DON'T pass the key are treated as
    "nothing unlocked", so gates fail closed:
      - source_url is blanked for YouTube courses (no URL leak on page load)
      - video_access_granted is False
      - videos list is empty

    This list is FOR READS ONLY (all serializers here are read-only).
    """

    def _unlocked_ids(self) -> set:
        return self.context.get("unlocked_course_ids", set())

    def _video_access_granted(self, course: Course) -> bool:
        return course.pk in self._unlocked_ids()

    def get_source_url(self, course: Course) -> str:
        """Blank the source URL for locked YouTube courses — no bypass link."""
        if course.provider == Course.Provider.YOUTUBE and not self._video_access_granted(course):
            return ""
        return course.source_url

    def get_video_access_granted(self, course: Course) -> bool:
        return self._video_access_granted(course)


class CourseListSerializer(VideoGateMixin, serializers.ModelSerializer):
    """
    Compact course representation for list views and combo course listings.
    Only includes fields needed for a course card.

    Video gate (see VideoGateMixin): for locked YouTube courses the
    source_url is blanked and video_access_granted is False.

    Output shape (must match frontend types/course.ts → CourseListItem exactly):
    {
      id, title, short_description, provider, provider_type, source_url,
      category, sub_category, level, age_group, format,
      duration_hours, duration_minutes, thumbnail_url,
      is_free, rating_average, rating_count, tags, video_access_granted
    }
    """

    source_url = serializers.SerializerMethodField(
        help_text="The course's source URL. Blanked by the video gate for "
        "locked YouTube courses (see VideoGateMixin).",
    )
    video_access_granted = serializers.SerializerMethodField(
        help_text="Whether the requesting user may watch this course's "
        "embedded videos / playlist.",
    )

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
            "video_access_granted",
        ]
        read_only_fields = fields


class CourseVideoItemSerializer(serializers.ModelSerializer):
    """
    One stored playlist video for a playlist-backed YouTube course.
    Only ever serialized inside CourseDetailSerializer — and only when the
    video gate is open.

    Output shape (must match frontend types/course.ts → CourseVideoItem exactly):
    { id, video_id, title, position, thumbnail_url, duration_seconds, published_at }
    """

    published_at = serializers.DateTimeField(
        allow_null=True,
        read_only=True,
        required=False,
        help_text="Video publish date on YouTube, or null when unreported.",
    )

    class Meta:
        model = CourseVideoItem
        fields = [
            "id",
            "video_id",
            "title",
            "position",
            "thumbnail_url",
            "duration_seconds",
            "published_at",
        ]
        read_only_fields = fields


class CourseDetailSerializer(VideoGateMixin, serializers.ModelSerializer):
    """
    Full course representation for the detail view.
    Includes all fields needed for the course detail page and the embed player.

    Video gate (see VideoGateMixin): locked YouTube courses return
    videos=[], video_access_granted=False, blanked source_url. Unlocked
    users get the stored playlist items in playlist order.

    Output shape (must match frontend types/course.ts → CourseDetail exactly):
    All CourseListItem fields + full_description, learning_outcomes,
    prerequisites, instructor, language, certificate_available, is_active, videos
    """

    videos = serializers.SerializerMethodField(
        help_text="Stored playlist videos, in playlist order. Empty when the "
        "video gate is locked or the course has no stored items.",
    )
    video_access_granted = serializers.SerializerMethodField(
        help_text="Whether the requesting user may watch this course's "
        "embedded videos / playlist.",
    )
    source_url = serializers.SerializerMethodField(
        help_text="The course's source URL. Blanked by the video gate for "
        "locked YouTube courses (see VideoGateMixin).",
    )

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
            "video_access_granted",
            "videos",
        ]
        read_only_fields = fields

    def get_videos(self, course: Course) -> list:
        if not self._video_access_granted(course):
            return []
        from apps.courses.services import CourseService

        serializer = CourseVideoItemSerializer(
            CourseService.get_course_videos(course), many=True
        )
        return serializer.data