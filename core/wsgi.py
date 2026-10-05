"""
WSGI config for stem_platform project.
Used by gunicorn in production (Render/Railway).
"""

import os
from django.core.wsgi import get_wsgi_application

# Hard pin, not setdefault: a stray DJANGO_SETTINGS_MODULE in the hosting
# environment (e.g. a leftover dev value on Render) must never override this —
# gunicorn would boot with the dev-only debug_toolbar app, which production
# requirements never install, and crash-loop. Local runserver is unaffected:
# manage.py configures development settings before this module is imported.
os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings.production"
application = get_wsgi_application()