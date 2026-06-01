"""
User views.

Request/response handling only. No business logic.
All logic is delegated to users/services.py.

Rules enforced:
- Rule 3: Views call services only
- Rule 7: Backend-owned analytics events fired from views per analytics/events.py
- Rule 9: No hidden side effects in views

Phase 4 additions:
- USER_SIGNED_UP fired from RegisterView.post() after successful registration
- USER_LOGGED_IN fired from LoginView.post() after successful authentication
- USER_PROFILE_UPDATED fired from MeView.patch() after successful profile update
"""

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.analytics.events import USER_LOGGED_IN, USER_PROFILE_UPDATED, USER_SIGNED_UP
from apps.analytics.services import AnalyticsService
from apps.users.serializers import (
    LoginSerializer,
    RegisterSerializer,
    UpdateProfileSerializer,
    UserSerializer,
)
from apps.users.services import UserProfileService, UserService

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    POST /auth/register/
    Register a new user with email and password.
    Returns the user object and JWT tokens on success.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            user = UserService.register_user(
                email=data["email"],
                password=data["password"],
                display_name=data.get("display_name", ""),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # USER_SIGNED_UP
        # OWNER: backend — see analytics/events.py
        # Fired after successful registration, before response is returned.
        # Rule 9: fire_event() is called explicitly and separately from service logic.
        AnalyticsService.fire_event(
            event_name=USER_SIGNED_UP,
            user_id=str(user.pk),
            properties={
                "email": user.email,
                "registration_method": "email_password",
            },
        )

        tokens = _generate_tokens(user)
        user_data = UserSerializer(user).data
        return Response(
            {"user": user_data, **tokens},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /auth/login/
    Authenticate with email and password.
    Returns the user object and JWT tokens on success.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = UserService.authenticate_user(
            email=data["email"],
            password=data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # USER_LOGGED_IN
        # OWNER: backend — see analytics/events.py
        # Fired after successful authentication, before response is returned.
        AnalyticsService.fire_event(
            event_name=USER_LOGGED_IN,
            user_id=str(user.pk),
            properties={
                "login_method": "email_password",
            },
        )

        tokens = _generate_tokens(user)
        user_data = UserSerializer(user).data
        return Response({"user": user_data, **tokens}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /auth/logout/
    Blacklist the provided refresh token.
    Requires: { "refresh": "<refresh_token>" }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            # Token already invalid or blacklisted — treat as successful logout
            pass

        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


class TokenRefreshView(APIView):
    """
    POST /auth/token/refresh/
    Exchange a valid refresh token for a new access token.
    Delegates entirely to simplejwt — this view is a thin pass-through.

    Note: The actual endpoint is registered via simplejwt's TokenRefreshView in urls.py.
    This class exists only as documentation of the endpoint.
    """

    pass


class MeView(APIView):
    """
    GET  /auth/me/  → Return the authenticated user's profile
    PATCH /auth/me/ → Update the authenticated user's profile
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = UserService.get_user_by_id(request.user.pk)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request: Request) -> Response:
        serializer = UpdateProfileSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            UserProfileService.update_profile(request.user, serializer.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # USER_PROFILE_UPDATED
        # OWNER: backend — see analytics/events.py
        # Fired after successful profile update.
        AnalyticsService.fire_event(
            event_name=USER_PROFILE_UPDATED,
            user_id=str(request.user.pk),
            properties={
                "updated_fields": list(serializer.validated_data.keys()),
            },
        )

        # Re-fetch to return updated data
        user = UserService.get_user_by_id(request.user.pk)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _generate_tokens(user) -> dict:
    """
    Generate access and refresh JWT tokens for a user.
    Kept in this module because it is only used by auth views.
    Not a service — no business logic, just token construction.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }