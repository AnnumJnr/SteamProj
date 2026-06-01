"""
Progress URL patterns.

All progress and saved item endpoints are under /api/progress/.
"""

from django.urls import path

from apps.progress.views import (
    MarkCourseCompleteView,
    MarkCourseStartedView,
    ProgressSummaryView,
    SavedComboDetailView,
    SavedCombosListView,
    SavedCourseDetailView,
    SavedCoursesListView,
    UserProgressListView,
    UnenrollCourseView,
)

urlpatterns = [
    # Progress listing and summary
    path("", UserProgressListView.as_view(), name="progress-list"),
    path("summary/", ProgressSummaryView.as_view(), name="progress-summary"),

    # Self-reported progress actions
    path("start/", MarkCourseStartedView.as_view(), name="progress-start"),
    path("complete/", MarkCourseCompleteView.as_view(), name="progress-complete"),

    # Saved courses
    path("saved/courses/", SavedCoursesListView.as_view(), name="saved-courses-list"),
    path("saved/courses/<uuid:course_id>/", SavedCourseDetailView.as_view(), name="saved-course-detail"),

    # Saved combos
    path("saved/combos/", SavedCombosListView.as_view(), name="saved-combos-list"),
    path("saved/combos/<uuid:combo_id>/", SavedComboDetailView.as_view(), name="saved-combo-detail"),
    
    path("<uuid:course_id>/", UnenrollCourseView.as_view(), name="progress-unenroll"),
]