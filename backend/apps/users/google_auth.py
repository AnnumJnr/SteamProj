"""
Google OAuth → JWT token exchange.

Flow:
1. Frontend redirects user to Google OAuth via allauth: GET /accounts/google/login/
2. Google redirects back to allauth callback: GET /accounts/google/login/callback/
3. allauth creates/fetches the User and logs them into the Django session
4. Frontend calls this endpoint with the session to exchange for JWT tokens

Alternative flow (for SPA / mobile — token-based):
1. Frontend obtains a Google ID token client-side (e.g. via Google Sign-In JS)
2. Frontend POSTs the ID token to POST /api/auth/google/
3. This view verifies it, creates/fetches the user, returns JWT tokens

This file implements the token-based flow (Step 2 alternative), which works
cleanly with a Next.js frontend that manages its own Google Sign-In.

Dependency: google-auth package (add to requirements if not present)
Install: pip install google-auth

Phase 4 change:
- Removed # TEMPORARY UserProfile.objects.create() block.
  Profile is now created by the post_save signal in users/signals.py → on_user_created().
  After signal creates the profile with defaults, this flow enriches it with
  display_name and avatar_url from Google's ID token payload.
"""

import logging

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User, UserProfile

logger = logging.getLogger(__name__)


class GoogleAuthView(APIView):
    """
    POST /api/auth/google/

    Accepts a Google ID token from the frontend, verifies it with Google,
    then creates or retrieves the platform user and returns JWT tokens.

    Request body:
    { "id_token": "<google_id_token_string>" }

    Response (201 on new user, 200 on existing):
    {
      "user": { ...UserSerializer output... },
      "access": "<jwt_access_token>",
      "refresh": "<jwt_refresh_token>",
      "created": true | false
    }

    Error responses:
    - 400: id_token missing or invalid format
    - 401: Google token verification failed
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        google_id_token = request.data.get("id_token")
        if not google_id_token:
            return Response(
                {"detail": "id_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the Google ID token
        try:
            id_info = id_token.verify_oauth2_token(
                google_id_token,
                google_requests.Request(),
                settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"],
            )
        except ValueError as e:
            logger.warning("GoogleAuthView: Token verification failed: %s", str(e))
            return Response(
                {"detail": "Invalid or expired Google token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = id_info.get("email")
        if not email:
            return Response(
                {"detail": "Google account does not have an associated email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not id_info.get("email_verified"):
            return Response(
                {"detail": "Google account email is not verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create or retrieve the user.
        # Profile creation is handled by the post_save signal (users/signals.py).
        # For new users, the signal creates the profile with defaults; we enrich
        # it with Google data immediately after.
        user, created = _get_or_create_google_user(
            email=email,
            display_name=id_info.get("name", ""),
            avatar_url=id_info.get("picture", ""),
        )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        tokens = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        from apps.users.serializers import UserSerializer
        user_data = UserSerializer(
            User.objects.select_related("profile").get(pk=user.pk)
        ).data

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        logger.info(
            "GoogleAuthView: %s user via Google OAuth: %s",
            "New" if created else "Existing",
            email,
        )

        return Response(
            {"user": user_data, "created": created, **tokens},
            status=response_status,
        )


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_or_create_google_user(email: str, display_name: str, avatar_url: str):
    """
    Retrieve an existing user by email or create a new one for a Google OAuth login.

    Google users have no password — Django's set_unusable_password() is called,
    which prevents email+password login for this account while keeping auth functional.

    For NEW users:
    - User.objects.create() fires the post_save signal → on_user_created()
    - Signal creates UserProfile with default values (display_name="", avatar_url="")
    - This function then enriches the profile with the Google display_name and avatar_url
    - Signal also dispatches the welcome email task

    For EXISTING users:
    - Email verification status is updated if not yet verified
    - No profile changes (user may have customised their profile since signup)

    Returns: (user, created) tuple
    """
    try:
        user = User.objects.get(email__iexact=email)
        created = False

        # Update email verification status — Google has already verified it
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified", "updated_at"])

    except User.DoesNotExist:
        # Create new user — no password for OAuth users.
        # post_save signal fires here → creates UserProfile with defaults.
        user = User.objects.create(email=email, is_email_verified=True)
        user.set_unusable_password()
        user.save(update_fields=["password"])

        # Enrich the profile the signal just created with Google's data.
        # The signal creates display_name="" and avatar_url="" by default.
        # We update only if Google provided values — do not overwrite with empty strings.
        _enrich_profile_from_google(
            user=user,
            display_name=display_name,
            avatar_url=avatar_url,
        )

        created = True
        logger.info("GoogleAuthView: New user created via Google OAuth: %s", email)

    return user, created


def _enrich_profile_from_google(user: User, display_name: str, avatar_url: str) -> None:
    """
    Update a new user's profile with data from Google's ID token.

    Called immediately after user creation, once the post_save signal has
    created the profile with default values. Only updates fields that have
    a non-empty value from Google — never overwrites with empty strings.

    Args:
        user:         The newly created User instance.
        display_name: Name from Google ID token (may be empty string).
        avatar_url:   Profile picture URL from Google ID token (may be empty).

    Rule 9: This function updates the profile and nothing else.
    No events fired, no tasks dispatched.
    """
    fields_to_update = []

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        # Signal failed to create the profile — create it now as recovery.
        logger.warning(
            "_enrich_profile_from_google: Profile missing for %s. Creating now.",
            user.email,
        )
        profile = UserProfile.objects.create(user=user)

    if display_name.strip():
        profile.display_name = display_name.strip()
        fields_to_update.append("display_name")

    if avatar_url.strip():
        profile.avatar_url = avatar_url.strip()
        fields_to_update.append("avatar_url")

    if fields_to_update:
        fields_to_update.append("updated_at")
        profile.save(update_fields=fields_to_update)
        logger.info(
            "_enrich_profile_from_google: Enriched profile for %s with fields %s",
            user.email,
            fields_to_update,
        )