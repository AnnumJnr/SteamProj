"""
Progress views.

Request/response handling only. No business logic.
All logic is delegated to progress/services.py.

Rules enforced:
- Rule 3: Views call services only
- Rule 9: No hidden side effects in views
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.progress.serializers import (
    MarkCourseActionSerializer,
    ProgressSummarySerializer,
    SavedComboSerializer,
    SavedCourseSerializer,
    SaveItemSerializer,
    UserProgressSerializer,
)
from apps.progress.services import UserProgressService, UserSavedItemsService
from common.pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


class UserProgressListView(APIView):
    """
    GET /progress/
    Return all progress records for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        queryset = UserProgressService.get_user_progress(request.user.pk)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = UserProgressSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ProgressSummaryView(APIView):
    """
    GET /progress/summary/
    Return aggregate progress counts for the authenticated user's dashboard.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        summary = UserProgressService.get_progress_summary(request.user.pk)
        serializer = ProgressSummarySerializer(summary)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarkCourseStartedView(APIView):
    """
    POST /progress/start/
    Mark a course as in-progress for the authenticated user.
    Body: { "course_id": "<uuid>" }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = MarkCourseActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            progress = UserProgressService.mark_course_started(
                request.user,
                serializer.validated_data["course_id"],
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(UserProgressSerializer(progress).data, status=status.HTTP_200_OK)


class MarkCourseCompleteView(APIView):
    """
    POST /progress/complete/
    Mark a course as completed for the authenticated user (self-reported).
    Body: { "course_id": "<uuid>" }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = MarkCourseActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            progress = UserProgressService.mark_course_complete(
                request.user,
                serializer.validated_data["course_id"],
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(UserProgressSerializer(progress).data, status=status.HTTP_200_OK)


# ─── Saved Courses ────────────────────────────────────────────────────────────

class SavedCoursesListView(APIView):
    """
    GET  /progress/saved/courses/         → List all saved courses
    POST /progress/saved/courses/         → Save a course
    Body (POST): { "item_id": "<course_uuid>" }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        queryset = UserSavedItemsService.get_saved_courses(request.user.pk)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = SavedCourseSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = SaveItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            saved = UserSavedItemsService.save_course(
                request.user,
                serializer.validated_data["item_id"],
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SavedCourseSerializer(saved).data, status=status.HTTP_201_CREATED)


class SavedCourseDetailView(APIView):
    """
    DELETE /progress/saved/courses/{course_id}/
    Remove a saved course.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, course_id) -> Response:
        try:
            UserSavedItemsService.unsave_course(request.user, course_id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Saved Combos ─────────────────────────────────────────────────────────────

class SavedCombosListView(APIView):
    """
    GET  /progress/saved/combos/         → List all saved combos
    POST /progress/saved/combos/         → Save a combo
    Body (POST): { "item_id": "<combo_uuid>" }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        queryset = UserSavedItemsService.get_saved_combos(request.user.pk)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = SavedComboSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = SaveItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            saved = UserSavedItemsService.save_combo(
                request.user,
                serializer.validated_data["item_id"],
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SavedComboSerializer(saved).data, status=status.HTTP_201_CREATED)


class SavedComboDetailView(APIView):
    """
    DELETE /progress/saved/combos/{combo_id}/
    Remove a saved combo.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, combo_id) -> Response:
        try:
            UserSavedItemsService.unsave_combo(request.user, combo_id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)
    

class UnenrollCourseView(APIView):
    """DELETE /progress/{course_id}/ — remove all progress for a course."""
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, course_id) -> Response:
        UserProgressService.delete_course_progress(request.user, course_id)
        return Response(status=status.HTTP_204_NO_CONTENT)