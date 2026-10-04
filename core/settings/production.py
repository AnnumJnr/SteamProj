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

# ─── Background task dispatch ─────────────────────────────────────────────────
#
# No Celery worker is deployed on Render, so tasks queued via the Redis broker
# would never be consumed — and when the broker is slow or unreachable, the
# synchronous .delay() publish blocks the HTTP request for tens of seconds
# (register/login hung ~20s+ and timed out client-side even though the DB
# work succeeded). INLINE_TASK_DISPATCH switches dispatch to daemon threads
# that execute the task body directly (see common/tasks.py): the request path
# never touches the broker, and PostHog delivery / welcome emails actually run.
# Set to False (and deploy a worker) if broker-based dispatch is reintroduced.
# ─── Transactional email ──────────────────────────────────────────────────────
#
# Render blocks outbound SMTP connections: the welcome email's smtplib connect
# to smtp-relay.brevo.com:587 hung ~133s and failed with TimeoutError [Errno
# 110] (2026-10-04 log). HTTPS egress is allowed, so when BREVO_API_KEY is set
# (Brevo → SMTP & API → API Keys — a different credential from the SMTP key)
# email is sent via the Brevo HTTP API instead of SMTP. Without the key the
# SMTP backend is kept, unchanged. Sender must be a verified sender in Brevo
# (set DEFAULT_FROM_EMAIL accordingly, e.g. the account owner's email).
if BREVO_API_KEY:  # noqa: F405 — defined in base.py
    EMAIL_BACKEND = "common.brevo_backend.BrevoApiBackend"

INLINE_TASK_DISPATCH = True

# Security headers
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
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
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# The API uses JWT headers, but Django admin still uses CSRF protection.
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    cast=Csv(),
    default="",
)

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