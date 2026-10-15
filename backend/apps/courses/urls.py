"""
Course URL patterns.

All course endpoints are under /api/courses/.
"""

from django.urls import path

from apps.courses.views import CourseDetailView, CourseListView

urlpatterns = [
    path("", CourseListView.as_view(), name="course-list"),
    path("<uuid:course_id>/", CourseDetailView.as_view(), name="course-detail"),
]