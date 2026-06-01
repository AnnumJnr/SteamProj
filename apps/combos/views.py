"""
Combo views.

Request/response handling only. No business logic.
All logic is delegated to combos/services.py.

Rules enforced:
- Rule 3: Views call services only
- Rule 9: No hidden side effects in views
"""

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.combos.serializers import (
    ComboDetailSerializer,
    ComboListSerializer,
    ComboRatingSerializer,
    CreateComboRatingSerializer,
    CreateComboSerializer,
    UpdateComboSerializer,
)
from apps.combos.services import ComboRatingService, ComboService
from apps.progress.serializers import ComboProgressSerializer
from common.pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


class ComboListView(APIView):
    """
    GET  /combos/  → List public combos (paginated, filtered)
    POST /combos/  → Create a new combo (authenticated)

    GET query parameters (all optional):
    - category       : STEM category
    - difficulty     : Beginner | Intermediate | Advanced | Mixed
    - recommended_age: Kids | Teens | Adults | All Ages
    - search         : Keyword search on title
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request: Request) -> Response:
        queryset = ComboService.get_combo_list(
            category=request.query_params.get("category"),
            difficulty=request.query_params.get("difficulty"),
            recommended_age=request.query_params.get("recommended_age"),
            search=request.query_params.get("search"),
        )

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ComboListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = CreateComboSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            combo = ComboService.create_combo(request.user, serializer.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ComboDetailSerializer(combo).data,
            status=status.HTTP_201_CREATED,
        )


class ComboDetailView(APIView):
    """
    GET    /combos/{id}/  → Retrieve a combo (public or owned)
    PATCH  /combos/{id}/  → Update a combo (owner or admin only)
    DELETE /combos/{id}/  → Delete a combo (owner or admin only)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request: Request, combo_id) -> Response:
        user = request.user if request.user.is_authenticated else None
        combo = ComboService.get_combo_detail(combo_id, user=user)

        if combo is None:
            return Response(
                {"detail": "Combo not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ComboDetailSerializer(combo)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request: Request, combo_id) -> Response:
        combo = ComboService.get_combo_detail(combo_id, user=request.user)
        if combo is None:
            return Response({"detail": "Combo not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ownership check is enforced in the service
        serializer = UpdateComboSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated_combo = ComboService.update_combo(combo, request.user, serializer.validated_data)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ComboDetailSerializer(updated_combo).data, status=status.HTTP_200_OK)

    def delete(self, request: Request, combo_id) -> Response:
        combo = ComboService.get_combo_detail(combo_id, user=request.user)
        if combo is None:
            return Response({"detail": "Combo not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            ComboService.delete_combo(combo, request.user)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserComboListView(APIView):
    """
    GET /combos/mine/
    Return all combos created by the authenticated user (public and private).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        queryset = ComboService.get_user_combos(request.user.pk)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ComboListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ComboProgressView(APIView):
    """
    GET /combos/{id}/progress/
    Return the authenticated user's progress through a specific combo.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, combo_id) -> Response:
        combo = ComboService.get_combo_detail(combo_id, user=request.user)
        if combo is None:
            return Response({"detail": "Combo not found."}, status=status.HTTP_404_NOT_FOUND)

        progress = ComboService.get_combo_progress(combo_id, request.user.pk)
        serializer = ComboProgressSerializer(progress)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ComboRatingView(APIView):
    """
    POST   /combos/{id}/rate/   → Submit or update a rating
    DELETE /combos/{id}/rate/   → Remove your rating
    GET    /combos/{id}/ratings/ → List all ratings for a combo (public)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def post(self, request: Request, combo_id) -> Response:
        combo = ComboService.get_combo_detail(combo_id, user=request.user)
        if combo is None:
            return Response({"detail": "Combo not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CreateComboRatingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            rating = ComboRatingService.rate_combo(
                combo=combo,
                user=request.user,
                rating=serializer.validated_data["rating"],
                review=serializer.validated_data.get("review", ""),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ComboRatingSerializer(rating).data, status=status.HTTP_200_OK)

    def delete(self, request: Request, combo_id) -> Response:
        combo = ComboService.get_combo_detail(combo_id, user=request.user)
        if combo is None:
            return Response({"detail": "Combo not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            ComboRatingService.delete_rating(combo, request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ComboRatingsListView(APIView):
    """
    GET /combos/{id}/ratings/
    List all ratings for a public combo.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, combo_id) -> Response:
        user = request.user if request.user.is_authenticated else None
        combo = ComboService.get_combo_detail(combo_id, user=user)
        if combo is None:
            return Response({"detail": "Combo not found."}, status=status.HTTP_404_NOT_FOUND)

        from apps.combos.querysets import ComboRatingQueryset
        ratings_qs = ComboRatingQueryset.get_ratings_for_combo(combo_id)

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(ratings_qs, request)
        serializer = ComboRatingSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ComboCourseDetailView(APIView):
    """
    DELETE /combos/{combo_id}/courses/{course_id}/
    Remove a single course from a combo.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, combo_id, course_id) -> Response:
        combo = ComboService.get_combo_detail(combo_id, user=request.user)
        if combo is None:
            return Response({"detail": "Combo not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check ownership
        if combo.created_by_user_id != request.user.pk and not request.user.is_staff:
            return Response({"detail": "You do not have permission to edit this combo."}, 
                          status=status.HTTP_403_FORBIDDEN)

        try:
            ComboService.remove_course_from_combo(combo, course_id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)