"""
ASGI config for stem_platform project.
Reserved for future WebSocket / async support.
Currently not used — WSGI is the active entry point.
"""

import os
from django.core.asgi import get_asgi_application

# Hard pin, not setdefault — same rationale as wsgi.py: an ASGI server must
# never boot with development settings, which import the uninstalled
# debug_toolbar app in production.
os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings.production"
application = get_asgi_application()