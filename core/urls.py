"""
Root URL configuration.
All app-level URLs are included here with their namespace prefixes.
API versioning via /api/v1/ prefix applied to all app routes.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    # Django admin — MVP admin panel
    path("admin/", admin.site.urls),

    # Authentication endpoints
    path("api/v1/auth/", include("apps.users.urls")),

    # Core API endpoints
    path("api/v1/courses/", include("apps.courses.urls")),
    path("api/v1/combos/", include("apps.combos.urls")),
    path("api/v1/progress/", include("apps.progress.urls")),

    # django-allauth social auth URLs
    path("accounts/", include("allauth.urls")),
]

# Debug toolbar — development only
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns