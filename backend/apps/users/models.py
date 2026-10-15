"""
User models.

User         — custom user extending AbstractBaseUser, auth identity
UserProfile  — extended profile data (age group, interests, display name)

Relationship: User → UserProfile is one-to-one, created via signal on user creation.
"""

import logging

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from common.models import TimestampedModel

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    """
    Custom manager for the User model.
    Required because we use email as the unique identifier instead of username.
    """

    def create_user(self, email: str, password: str = None, **extra_fields):
        """Create and save a standard user with the given email and password."""
        if not email:
            raise ValueError("A user must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        logger.info("User created: %s", email)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    """
    Platform user account.

    Email is the primary identifier. Username is not used.
    Google OAuth users will have no password set (unusable password).
    """

    email = models.EmailField(
        unique=True,
        help_text="Primary identifier. Used for login and notifications.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive users cannot log in. Use this instead of deleting accounts.",
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Staff users can access the Django admin panel.",
    )
    is_email_verified = models.BooleanField(
        default=False,
        help_text="True once the user has confirmed their email address.",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []   # email + password are the only required fields

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        db_table = "users"

    def __str__(self):
        return self.email


class UserProfile(TimestampedModel):
    """
    Extended profile data for a user.

    Created automatically when a User is created (see apps/users/signals.py).
    Stores display preferences, age group, and learning interests.
    """

    class AgeGroup(models.TextChoices):
        KIDS = "Kids", "Kids (under 13)"
        TEENS = "Teens", "Teens (13–17)"
        ADULTS = "Adults", "Adults (18+)"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="The user this profile belongs to.",
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional display name shown on the platform.",
    )
    avatar_url = models.URLField(
        blank=True,
        default="",
        help_text="External URL to the user's avatar image. Stored as URL only (no local storage at MVP).",
    )
    age_group = models.CharField(
        max_length=10,
        choices=AgeGroup.choices,
        default=AgeGroup.ADULTS,
        help_text="Used to filter and recommend age-appropriate content.",
    )
    bio = models.TextField(
        blank=True,
        default="",
        max_length=500,
        help_text="Short user bio, optional.",
    )
    interests = models.JSONField(
        default=list,
        blank=True,
        help_text="List of STEM category interests e.g. ['Computer Science', 'Mathematics'].",
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        db_table = "user_profiles"

    def __str__(self):
        return f"Profile({self.user.email})"