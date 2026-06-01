"""
Users app tasks.

The welcome email task lives in notifications/tasks.py (correct architectural home —
the notifications app owns all email sending logic).

This module re-exports it so that users/signals.py can import from a consistent
location within the users app, and to keep the import path readable.

If new user-specific async tasks are needed in future (e.g. account deletion cleanup,
bulk profile migration), add them here directly.

Call chain reminder:
    users/signals.py → send_welcome_email_task.delay(user_id)
        → notifications/tasks.py → NotificationService.send_welcome_email()
"""

# Re-export for clean import in users/signals.py.
# MULTI-USE: Used by users/signals.py → on_user_created()
# The authoritative definition is: notifications/tasks.py → send_welcome_email_task
from apps.notifications.tasks import send_welcome_email_task  # noqa: F401

__all__ = ["send_welcome_email_task"]