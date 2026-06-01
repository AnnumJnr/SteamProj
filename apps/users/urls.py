"""
User URL patterns.

Auth endpoints: /auth/
Profile endpoint: /auth/me/

JWT token refresh is handled by simplejwt's built-in view.
Google OAuth callback is handled by allauth.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.google_auth import GoogleAuthView
from apps.users.views import LoginView, LogoutView, MeView, RegisterView

urlpatterns = [
    # Registration and login
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),

    # JWT token refresh — simplejwt built-in view
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),

    # Google OAuth — accepts Google ID token, returns JWT tokens
    # Full OAuth redirect flow is handled by allauth at /accounts/google/login/
    path("google/", GoogleAuthView.as_view(), name="auth-google"),

    # Authenticated user profile
    path("me/", MeView.as_view(), name="auth-me"),
]