# Intentionally empty.
#
# Rule 12 requires this file to exist on every app, even when unused.
#
# Notifications are dispatched server-side only (Celery task → SMTP).
# There is no client-facing request/response shape to validate at MVP.
