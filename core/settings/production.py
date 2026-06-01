"""
Production settings.
Security-hardened. All secrets must come from environment variables.
Never commit secrets. Never set DEBUG=True here.
"""

from .base import *  # noqa: F401, F403
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from decouple import config

DEBUG = False

# Security headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# Static files served via whitenoise in production
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ─── Sentry ───────────────────────────────────────────────────────────────────
#
# Sentry captures:
# - Unhandled exceptions in Django views and middleware
# - Celery task exceptions (via celery integration)
# - Performance traces (transactions) for views and Celery tasks
#
# Setup:
# 1. Create a project at https://sentry.io → Django
# 2. Copy the DSN from Project Settings → Client Keys
# 3. Add SENTRY_DSN=https://...@sentry.io/... to your production .env
# 4. Add SENTRY_ENVIRONMENT=production to your production .env
#
# Tracing:
# SENTRY_TRACES_SAMPLE_RATE=0.1 means 10% of requests are traced.
# Start low and increase if you need more performance data.
# Set to 0 to disable tracing (error capture still works).
#
# Validation (once deployed):
# Trigger a deliberate error to confirm Sentry receives it:
#   raise Exception("Sentry test — delete this after confirming")
# Check the Sentry dashboard → Issues for the captured event.
 
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging as python_logging
 
SENTRY_DSN = config("SENTRY_DSN", default="")  # noqa: F405
SENTRY_ENVIRONMENT = config("SENTRY_ENVIRONMENT", default="production")  # noqa: F405
SENTRY_TRACES_SAMPLE_RATE = config("SENTRY_TRACES_SAMPLE_RATE", cast=float, default=0.1)  # noqa: F405
 
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        integrations=[
            DjangoIntegration(
                transaction_style="url",        # Group transactions by URL pattern
                middleware_spans=True,          # Trace middleware execution
                signals_spans=False,            # Don't trace signal handlers (too noisy)
                cache_spans=False,              # Don't trace cache calls at MVP
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,        # Track Beat task execution in Sentry Crons
                propagate_traces=True,          # Link Celery task traces to their parent request
            ),
            LoggingIntegration(
                level=python_logging.WARNING,   # Capture WARNING+ as Sentry breadcrumbs
                event_level=python_logging.ERROR,  # Send ERROR+ as Sentry events
            ),
        ],
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,     # Do not send PII (emails, IPs) to Sentry
        attach_stacktrace=True,     # Attach stack traces to all events, not just exceptions
    )
else:
    # SENTRY_DSN not configured — Sentry is disabled.
    # This is expected during initial deployment before Sentry is set up.
    # Do not use logger here — logging may not be initialised yet at settings load time.
    import sys
    print(
        "[WARNING][core.settings.production] SENTRY_DSN is not set. "
        "Sentry error tracking is disabled. Set SENTRY_DSN in .env to enable.",
        file=sys.stderr,
    )