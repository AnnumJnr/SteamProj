"""
Notification services.

Business logic for all platform notifications.
Tasks call services. Services call email builders (emails.py).

Rule 3: Services are the entry point for all notification business logic.
Rule 9: No hidden side effects — each function does exactly what it declares.
Rule 14: One responsibility per function.

MVP scope: Welcome email only.
Phase 2 scope: Combo/course progress reminders.
"""

import logging

from apps.notifications.emails import build_welcome_email

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Orchestrates platform email notifications.

    Each method:
    1. Gathers the data required to build the email
    2. Calls the appropriate email builder (emails.py)
    3. Sends the constructed message
    4. Logs the outcome

    No Celery task logic lives here — tasks.py handles async dispatch.
    No template construction lives here — emails.py handles that.
    """

    @staticmethod
    def send_welcome_email(user_id: int) -> bool:
        """
        Send the welcome email to a newly registered user.

        Called by: notifications/tasks.py → send_welcome_email_task

        Fetches the user, builds the email via build_welcome_email(),
        and sends it via Django's email backend (SMTP in production,
        console in development).

        Args:
            user_id: Primary key of the User who just registered.

        Returns:
            True if the email was sent successfully, False otherwise.

        Rule 9: This function sends an email and nothing else.
        No analytics events, no DB writes, no side effects.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.select_related("profile").get(pk=user_id)
        except User.DoesNotExist:
            logger.error(
                "NotificationService.send_welcome_email: User %s not found. "
                "Email not sent.",
                user_id,
            )
            return False

        display_name = ""
        if hasattr(user, "profile") and user.profile:
            display_name = user.profile.display_name or ""

        try:
            email = build_welcome_email(
                user_email=user.email,
                display_name=display_name,
            )
            email.send(fail_silently=False)
            logger.info(
                "NotificationService.send_welcome_email: Welcome email sent to %s",
                user.email,
            )
            return True

        except Exception:
            logger.error(
                "NotificationService.send_welcome_email: Failed to send welcome email "
                "to %s",
                user.email,
                exc_info=True,
            )
            return False