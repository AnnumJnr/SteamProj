"""
User services.

All business logic for User and UserProfile lives here.
Views call services. Services call querysets.

Rules enforced:
- Rule 1: Single source of truth for logic
- Rule 3: Services are the entry point for business logic
- Rule 5: Business validation lives here, not in serializers or models
- Rule 15: No direct model writes outside services

Phase 4 change:
- UserProfile creation removed from register_user().
  Profile is now created by the post_save signal in users/signals.py.
  This is the single authoritative location for profile creation.
"""

import logging

from django.contrib.auth import authenticate
from django.db import transaction

from apps.users.models import User, UserProfile
from apps.users.querysets import UserProfileQueryset, UserQueryset

logger = logging.getLogger(__name__)


class UserService:
    """
    Business logic for user registration, authentication, and account management.
    """

    @staticmethod
    @transaction.atomic
    def register_user(email: str, password: str, display_name: str = "") -> User:
        """
        Register a new user with email and password.

        Creates the User only. UserProfile is created automatically by the
        post_save signal in users/signals.py → on_user_created().

        If display_name is provided, the profile is updated after creation.
        The signal creates the profile with display_name="" (default); this
        service then enriches it with the caller-provided display_name.

        Business rules enforced:
        - Email must not already be registered
        - Password validation is handled by Django's AUTH_PASSWORD_VALIDATORS

        Raises:
            ValueError: If the email is already registered.
        """
        if UserQueryset.email_exists(email):
            logger.warning("UserService.register_user: Email already registered: %s", email)
            raise ValueError("An account with this email already exists.")

        # User creation fires the post_save signal → on_user_created()
        # which creates the UserProfile and dispatches the welcome email task.
        user = User.objects.create_user(email=email, password=password)

        # If a display_name was provided, update the profile the signal just created.
        # The signal creates profile with display_name="" — we enrich it here if needed.
        if display_name.strip():
            try:
                profile = user.profile
                profile.display_name = display_name.strip()
                profile.save(update_fields=["display_name", "updated_at"])
            except UserProfile.DoesNotExist:
                # Guard: signal should have created the profile, but if it failed,
                # the profile guard in UserProfileService.update_profile() handles recovery.
                logger.warning(
                    "UserService.register_user: Profile not found for user %s "
                    "when setting display_name. Signal may have failed.",
                    email,
                )

        logger.info("UserService.register_user: New user registered: %s", email)
        return user

    @staticmethod
    def authenticate_user(email: str, password: str) -> User | None:
        """
        Authenticate a user by email and password.
        Returns the User if credentials are valid, None otherwise.

        Note: JWT token generation happens in the view layer using simplejwt.
        Authentication (verifying credentials) is the responsibility of this service.
        """
        user = authenticate(username=email, password=password)
        if user is None:
            logger.warning("UserService.authenticate_user: Failed login attempt for %s", email)
            return None
        if not user.is_active:
            logger.warning("UserService.authenticate_user: Inactive user attempted login: %s", email)
            return None
        logger.info("UserService.authenticate_user: Successful login: %s", email)
        return user

    @staticmethod
    def get_user_by_id(user_id) -> User | None:
        """Return a user by ID with their profile pre-fetched."""
        return UserQueryset.get_with_profile(user_id)

    @staticmethod
    def mark_email_verified(user: User) -> User:
        """
        Mark a user's email as verified.
        Called after successful email confirmation.
        """
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified", "updated_at"])
        logger.info("UserService.mark_email_verified: Email verified for user %s", user.email)
        return user

    @staticmethod
    def deactivate_user(user: User) -> User:
        """
        Deactivate a user account. Preferred over deletion.
        Deactivated users cannot log in.
        """
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        logger.info("UserService.deactivate_user: User deactivated: %s", user.email)
        return user


class UserProfileService:
    """
    Business logic for user profile management.
    """

    @staticmethod
    def get_profile(user_id) -> UserProfile | None:
        """Return the profile for a given user_id."""
        return UserProfileQueryset.get_by_user_id(user_id)

    @staticmethod
    def update_profile(user: User, data: dict) -> UserProfile:
        """
        Update a user's profile with the provided data.
        Only updates fields present in the data dict.

        Allowed fields: display_name, avatar_url, age_group, bio, interests.

        Business rules enforced:
        - interests must be a list
        - age_group must be a valid AgeGroup choice

        Raises:
            ValueError: If interests is not a list.
            ValueError: If age_group is not a valid choice.
        """
        profile = UserProfileQueryset.get_by_user(user)
        if profile is None:
            # Guard: profile should always exist after registration (signal creates it).
            # If the signal failed, we create it here as recovery.
            logger.warning(
                "UserProfileService.update_profile: Profile missing for user %s. Creating now.",
                user.email,
            )
            profile = UserProfile.objects.create(user=user)

        allowed_fields = {"display_name", "avatar_url", "age_group", "bio", "interests"}
        update_fields = []

        for field, value in data.items():
            if field not in allowed_fields:
                continue  # Silently skip unknown fields — serializer already validated shape

            if field == "interests":
                if not isinstance(value, list):
                    raise ValueError("interests must be a list of strings.")

            if field == "age_group":
                valid_choices = [choice[0] for choice in UserProfile.AgeGroup.choices]
                if value not in valid_choices:
                    raise ValueError(
                        f"age_group must be one of: {', '.join(valid_choices)}."
                    )

            setattr(profile, field, value)
            update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            profile.save(update_fields=update_fields)
            logger.info(
                "UserProfileService.update_profile: Updated fields %s for user %s",
                update_fields,
                user.email,
            )

        return profile