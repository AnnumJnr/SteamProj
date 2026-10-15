"""
Custom DRF permission classes used across the platform.
All views reference these rather than inline permission logic.
"""

from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Grants access only if the requesting user is the owner of the object.
    The object must have a `user` or `created_by` attribute pointing to a User.

    Usage: permission_classes = [IsAuthenticated, IsOwner]
    """

    def has_object_permission(self, request, view, obj):
        # Check for `user` attribute first (e.g., UserProgress, UserSavedItems)
        if hasattr(obj, "user"):
            return obj.user == request.user
        # Check for `created_by` attribute (e.g., Combo)
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user
        return False


class IsAdminOrReadOnly(BasePermission):
    """
    Read access for any authenticated user.
    Write access (POST, PUT, PATCH, DELETE) restricted to admin users only.

    Usage: permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    """

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_permission(self, request, view):
        if request.method in self.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(BasePermission):
    """
    Grants access if the requesting user is the object owner OR an admin.

    Usage: permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user
        return False