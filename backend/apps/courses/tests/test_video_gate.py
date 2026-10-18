"""
Tests for the video gate — embedded videos / playlist data are only served
after a user starts a course.

Gate surface:
- apps/courses/serializers.py → VideoGateMixin (source_url blanking,
  video_access_granted, detail videos list)
- apps/courses/services.py → CourseService.get_unlocked_course_ids
- apps/courses/views.py → must pass the gate context (fails closed)

Rule 9: tests write only through services or ORM setup, never serializers.
"""

import pytest
from rest_framework.test import APIClient

from apps.courses.serializers import CourseDetailSerializer
from apps.courses.models import Course, CourseVideoItem
from apps.courses.services import CourseService
from apps.users.models import User

pytestmark = pytest.mark.django_db


def make_course(**overrides) -> Course:
    """A minimal active YouTube playlist course."""
    defaults = dict(
        title="Intro to Python",
        provider=Course.Provider.YOUTUBE,
        provider_type=Course.ProviderType.VIDEO_PLATFORM,
        source_url="https://www.youtube.com/playlist?list=PLtest123",
        category=Course.Category.COMPUTER_SCIENCE,
        level=Course.Level.BEGINNER,
        age_group=Course.AgeGroup.TEENS,
        format=Course.Format.VIDEO,
    )
    defaults.update(overrides)
    return Course.objects.create(**defaults)


def make_items(course: Course, count: int = 2) -> None:
    for i in range(count):
        CourseVideoItem.objects.create(
            course=course,
            video_id=f"vid{i}",
            title=f"Lesson {i + 1}",
            position=i,
        )


def make_user(email: str = "student@example.com") -> User:
    return User.objects.create_user(email=email)


def get_course(client: APIClient, course: Course) -> dict:
    response = client.get(f"/api/v1/courses/{course.pk}/")
    assert response.status_code == 200
    return response.json()


class TestVideoGateAnon:
    """Anonymous users: everything locked, no URL leak."""

    def test_anon_gets_locked_payload(self, api_client: APIClient):
        course = make_course()
        make_items(course)
        data = get_course(api_client, course)
        assert data["video_access_granted"] is False
        assert data["videos"] == []
        assert data["source_url"] == ""

    def test_anon_locked_even_without_items(self, api_client: APIClient):
        course = make_course()
        data = get_course(api_client, course)
        assert data["video_access_granted"] is False
        assert data["videos"] == []
        assert data["source_url"] == ""


class TestVideoGateAuthed:
    """Authenticated users unlock by starting the course."""

    def test_active_user_not_started_locked(self, api_client: APIClient):
        course = make_course()
        make_items(course)
        user = make_user()
        api_client.force_authenticate(user=user)
        data = get_course(api_client, course)
        assert data["video_access_granted"] is False
        assert data["videos"] == []
        assert data["source_url"] == ""

    def test_started_user_unlocked_with_items_in_order(
        self, api_client: APIClient
    ):
        course = make_course()
        make_items(course, 3)
        user = make_user()
        from apps.progress.services import UserProgressService

        UserProgressService.mark_course_started(user, course.pk)
        api_client.force_authenticate(user=user)
        data = get_course(api_client, course)
        assert data["video_access_granted"] is True
        assert data["source_url"] == course.source_url
        assert [v["video_id"] for v in data["videos"]] == ["vid0", "vid1", "vid2"]
        assert data["videos"][0]["title"] == "Lesson 1"
        assert data["videos"][0]["position"] == 0

    def test_completed_user_still_unlocked(self, api_client: APIClient):
        course = make_course()
        make_items(course)
        user = make_user()
        from apps.progress.services import UserProgressService

        UserProgressService.mark_course_complete(user, course.pk)
        api_client.force_authenticate(user=user)
        data = get_course(api_client, course)
        assert data["video_access_granted"] is True
        assert data["source_url"] == course.source_url

    def test_unenrolled_user_re_locked(self, api_client: APIClient):
        course = make_course()
        make_items(course)
        user = make_user()
        from apps.progress.services import UserProgressService

        UserProgressService.mark_course_started(user, course.pk)
        UserProgressService.unenroll_course(user, course.pk)
        api_client.force_authenticate(user=user)
        data = get_course(api_client, course)
        assert data["video_access_granted"] is False
        assert data["videos"] == []
        assert data["source_url"] == ""


class TestGateScope:
    """The gate covers YouTube only; other providers keep their URLs."""

    def test_non_youtube_course_keeps_source_url(self, api_client: APIClient):
        course = make_course(
            provider=Course.Provider.OPENSTAX,
            provider_type=Course.ProviderType.OPEN_TEXTBOOK,
            format=Course.Format.TEXT,
        )
        user = make_user()
        api_client.force_authenticate(user=user)
        data = get_course(api_client, course)
        assert data["video_access_granted"] is False
        assert data["source_url"] == course.source_url

    def test_missing_context_fails_closed(self):
        """A serializer directly instantiated without gate context stays locked."""
        course = make_course()
        serializer = CourseDetailSerializer(course)
        assert serializer.data["video_access_granted"] is False
        assert serializer.data["source_url"] == ""


class TestAccessService:
    """CourseService.get_unlocked_course_ids — the gate's source of truth."""

    def test_anonymous_returns_empty(self):
        from django.contrib.auth.models import AnonymousUser

        assert CourseService.get_unlocked_course_ids(AnonymousUser()) == set()

    def test_started_course_ids(self):
        course_a = make_course(title="A")
        make_course(title="B")
        user = make_user()
        from apps.progress.services import UserProgressService

        UserProgressService.mark_course_started(user, course_a.pk)
        unlocked = CourseService.get_unlocked_course_ids(user)
        assert unlocked == {course_a.pk}
