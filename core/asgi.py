"""
ASGI config for stem_platform project.
Reserved for future WebSocket / async support.
Currently not used — WSGI is the active entry point.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.production")
application = get_asgi_application()