"""
User querysets.

All database query logic for User and UserProfile lives here.
Views and services must never construct raw ORM queries outside this file.

Rule 4: Query logic must be centralized.
"""

import logging

from django.db.models import QuerySet

from apps.users.models import User, UserProfile

logger = logging.getLogger(__name__)


class UserQueryset:
    """
    All DB query logic for the User model.
    Methods return querysets or model instances — never response objects.
    """

    @staticmethod
    def get_by_id(user_id) -> User | None:
        """Return a User by primary key, or None if not found."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_email(email: str) -> User | None:
        """Return a User by email address (case-insensitive), or None if not found."""
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def email_exists(email: str) -> bool:
        """Return True if an account with this email already exists."""
        return User.objects.filter(email__iexact=email).exists()

    @staticmethod
    def get_active_users() -> QuerySet:
        """Return all active users."""
        return User.objects.filter(is_active=True)

    @staticmethod
    def get_with_profile(user_id) -> User | None:
        """
        Return a User with their profile pre-fetched to avoid N+1.
        Used when profile fields are needed alongside user fields.
        """
        try:
            return User.objects.select_related("profile").get(pk=user_id)
        except User.DoesNotExist:
            return None


class UserProfileQueryset:
    """
    All DB query logic for the UserProfile model.
    """

    @staticmethod
    def get_by_user(user: User) -> UserProfile | None:
        """Return the profile for a given user, or None if not found."""
        try:
            return UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return None

    @staticmethod
    def get_by_user_id(user_id) -> UserProfile | None:
        """Return the profile for a given user_id, or None if not found."""
        try:
            return UserProfile.objects.select_related("user").get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return None