# Intentionally empty.
#
# Rule 12 requires this file to exist on every app, even when unused.
#
# This app has no REST endpoints — it is triggered internally by other
# apps' signals (e.g. apps/users/signals.py) via Celery task dispatch,
# not by client HTTP requests.
