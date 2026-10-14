"""
User serializers.

Format and type validation only. No business logic.
Business rules live in users/services.py.

Rule 5: Serializers handle format and type validation only.
Rule 10: Frontend TypeScript types must match serializer output exactly.
"""

from rest_framework import serializers

from apps.users.models import User, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile — used in read and update operations.
    """

    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "avatar_url",
            "age_group",
            "bio",
            "interests",
        ]

    def validate_interests(self, value):
        """Interests must be a list of strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError("interests must be a list.")
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each interest must be a string.")
        return value


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the User model.
    Includes nested profile data.
    Used in: /auth/me endpoint, profile responses.

    Output shape (must match frontend types/user.ts exactly):
    {
      id, email, is_email_verified, is_staff, created_at,
      profile: { display_name, avatar_url, age_group, bio, interests }
    }
    """

    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "is_email_verified",
            "is_staff",
            "created_at",
            "profile",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """
    Validates registration input.
    Business logic (uniqueness check, user creation) lives in UserService.register_user().
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        min_length=8,
        write_only=True,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    display_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(self, data):
        """Validate that password and password_confirm match."""
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data


class LoginSerializer(serializers.Serializer):
    """
    Validates login input.
    Authentication logic lives in UserService.authenticate_user().
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )


class UpdateProfileSerializer(serializers.Serializer):
    """
    Validates profile update input (PATCH).
    All fields optional — only provided fields are updated.
    Business logic lives in UserProfileService.update_profile().
    """

    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True)
    age_group = serializers.ChoiceField(
        choices=UserProfile.AgeGroup.choices,
        required=False,
    )
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)
    interests = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )