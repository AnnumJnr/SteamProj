"""
Course views.

Request/response handling only. No business logic.
All logic is delegated to courses/services.py.

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

from apps.courses.serializers import CourseDetailSerializer, CourseListSerializer
from apps.courses.services import CourseService
from common.pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


class CourseListView(APIView):
    """
    GET /courses/
    Return a paginated, filtered list of active courses.

    Query parameters (all optional):
    - category     : STEM category (e.g. "Computer Science")
    - level        : Beginner | Intermediate | Advanced
    - age_group    : Kids | Teens | Adults
    - provider     : YouTube | freeCodeCamp | MIT OCW | OpenStax | CK-12 | Khan Academy
    - format       : Video | Text | Interactive
    - search       : Keyword search across title and tags
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        queryset = CourseService.get_course_list(
            category=request.query_params.get("category"),
            level=request.query_params.get("level"),
            age_group=request.query_params.get("age_group"),
            provider=request.query_params.get("provider"),
            format=request.query_params.get("format"),
            search=request.query_params.get("search"),
        )

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CourseListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class CourseDetailView(APIView):
    """
    GET /courses/{id}/
    Return the full detail for a single active course.

    YouTube courses: The source_url field is used by the frontend VideoPlayer component
    to embed the course. If embedding is blocked, the frontend redirects to source_url.
    # FALLBACK: Redirect to source_url in a new tab if YouTube embed is blocked
    # PRIMARY: frontend/components/courses/VideoPlayer.tsx → embed player
    # CONDITION: YouTube embed blocked by provider or browser policy
    # THRESHOLD: Not applicable — handled entirely client-side
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, course_id) -> Response:
        course = CourseService.get_course_detail(course_id)
        if course is None:
            return Response(
                {"detail": "Course not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CourseDetailSerializer(course)
        return Response(serializer.data, status=status.HTTP_200_OK)