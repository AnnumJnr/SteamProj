"""
Combo URL patterns.

All combo endpoints are under /api/combos/.
"""

from django.urls import path

from apps.combos.views import (
    ComboDetailView,
    ComboListView,
    ComboCourseDetailView,
    ComboProgressView,
    ComboRatingView,
    ComboRatingsListView,
    UserComboListView,
)

urlpatterns = [
    # Combo listing and creation
    path("", ComboListView.as_view(), name="combo-list"),

    # Current user's combos (public + private)
    path("mine/", UserComboListView.as_view(), name="combo-mine"),

    # Combo detail, update, delete
    path("<uuid:combo_id>/", ComboDetailView.as_view(), name="combo-detail"),

    # Progress through a specific combo
    path("<uuid:combo_id>/progress/", ComboProgressView.as_view(), name="combo-progress"),

    # Rating actions (POST to rate, DELETE to remove rating)
    path("<uuid:combo_id>/rate/", ComboRatingView.as_view(), name="combo-rate"),

    # Read-only list of all ratings for a combo
    path("<uuid:combo_id>/ratings/", ComboRatingsListView.as_view(), name="combo-ratings"),

    path("<uuid:combo_id>/courses/<uuid:course_id>/", 
        ComboCourseDetailView.as_view(), 
        name="combo-course-detail"),
]