"""
Notification Celery tasks.

Tasks are thin wrappers. All logic lives in notifications/services.py.

Rule 6: Tasks may contain async delivery logic but no business logic.
Rule 9: send_welcome_email_task sends the email and nothing else.
         No DB writes, no analytics events inside this task.

Call chain:
    users/signals.py → send_welcome_email_task.delay(user_id)
        → NotificationService.send_welcome_email(user_id)
            → build_welcome_email() → email.send()
"""

import logging

from celery import shared_task

from apps.notifications.services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,   # seconds between retries
    name="notifications.send_welcome_email",
)
def send_welcome_email_task(self, user_id: int) -> dict:
    """
    Send the welcome email to a newly registered user.

    Dispatched by: apps/users/signals.py → on_user_created()
    Executed by: Celery worker (or inline in CELERY_TASK_ALWAYS_EAGER dev mode)

    Retries up to 3 times with a 60-second delay between attempts.
    If all retries are exhausted, logs an error — no further escalation at MVP.

    Args:
        user_id: Primary key of the User to email.

    Returns:
        dict with status and user_id for Celery result backend.

    Rule 9: This task does exactly one thing — send the welcome email.
    No analytics events are fired here. USER_SIGNED_UP is fired from
    users/views.py → RegisterView and users/google_auth.py → GoogleAuthView,
    which are the authoritative emitters per analytics/events.py.
    """
    logger.info(
        "send_welcome_email_task: Attempting welcome email for user_id=%s "
        "(attempt %s/%s)",
        user_id,
        self.request.retries + 1,
        self.max_retries + 1,
    )

    try:
        success = NotificationService.send_welcome_email(user_id)

        if success:
            logger.info(
                "send_welcome_email_task: Welcome email delivered for user_id=%s",
                user_id,
            )
            return {"status": "sent", "user_id": user_id}
        else:
            # NotificationService returned False — user not found or send failed.
            # Do not retry a missing user (they won't appear on retry either).
            # For send failures, NotificationService already logs the error.
            logger.warning(
                "send_welcome_email_task: NotificationService returned False "
                "for user_id=%s. Not retrying.",
                user_id,
            )
            return {"status": "failed", "user_id": user_id}

    except Exception as exc:
        logger.error(
            "send_welcome_email_task: Unexpected error for user_id=%s: %s. "
            "Retrying in %s seconds.",
            user_id,
            str(exc),
            self.default_retry_delay,
            exc_info=True,
        )
        raise self.retry(exc=exc)