"""
Development settings.
Overrides base settings for local development only.
Never use DEBUG=True or these settings in production.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Development-only: allow all hosts locally
ALLOWED_HOSTS = ["*"]

# Use console email backend in development — no real emails sent
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Django Debug Toolbar — active in dev only
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# Looser CORS in development
CORS_ALLOW_ALL_ORIGINS = True

# ─── Celery (eager mode — no Redis required locally) ─────────────────────────
#
# CELERY_TASK_ALWAYS_EAGER causes all .delay() and .apply_async() calls to
# execute synchronously in the same process, inline, without a broker or worker.
#
# This means:
# - Welcome emails execute immediately on registration (printed to console via EMAIL_BACKEND above)
# - Analytics events dispatch inline — PostHog delivery is attempted synchronously
# - Beat scheduling is NOT testable locally — that requires a running worker + Redis
#
# IMPORTANT: CELERY_TASK_ALWAYS_EAGER must NEVER appear in production.py.
# Celery 5 deprecated the settings-level config name in favour of app.conf — but
# Django-Celery reads CELERY_TASK_ALWAYS_EAGER from Django settings via the
# CELERY_TASK_ALWAYS_EAGER key in CELERY_TASK_ALWAYS_EAGER. Both are honoured.
# We set it here AND ensure core/celery.py reads it via app.config_from_object().
#
# Validation approach:
# - Local: CELERY_TASK_ALWAYS_EAGER = True → tasks run inline, no broker needed
# - Production: Real Redis on Render/Railway → tasks queued and executed by worker
 
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True   # Exceptions in tasks surface immediately in dev