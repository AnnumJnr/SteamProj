"""
Analytics models.

EventLog — local backup of every analytics event fired to PostHog.

Purpose: If PostHog is unavailable or an event fails to send, the local
log provides a recovery mechanism. Events can be replayed from this table.

Rule 8 (observability): All critical flows must be visible and measurable.
"""

import logging

from django.db import models

from common.models import TimestampedModel

logger = logging.getLogger(__name__)


class EventLog(TimestampedModel):
    """
    Local record of every analytics event sent (or attempted to send) to PostHog.

    event_name values are defined as constants in apps/analytics/events.py.
    This table is append-only — events are never edited after creation.
    """

    event_name = models.CharField(
        max_length=100,
        help_text="Event name constant from analytics/events.py e.g. 'user_signed_up'.",
    )
    user_id = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="UUID of the user who triggered this event. Empty for anonymous events.",
    )
    properties = models.JSONField(
        default=dict,
        help_text="Event-specific payload. Shape varies by event_name.",
    )
    context = models.JSONField(
        default=dict,
        help_text="Platform context: platform, device, country.",
    )
    sent_to_posthog = models.BooleanField(
        default=False,
        help_text="True once successfully delivered to PostHog.",
    )
    posthog_error = models.TextField(
        blank=True,
        default="",
        help_text="Error message if PostHog delivery failed.",
    )
    fired_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this event was first recorded locally.",
    )

    class Meta:
        verbose_name = "Event Log"
        verbose_name_plural = "Event Logs"
        db_table = "event_logs"
        indexes = [
            models.Index(fields=["event_name"], name="idx_event_name"),
            models.Index(fields=["user_id"], name="idx_event_user"),
            models.Index(fields=["sent_to_posthog"], name="idx_event_sent"),
            models.Index(fields=["fired_at"], name="idx_event_fired_at"),
        ]
        ordering = ["-fired_at"]

    def __str__(self):
        return f"EventLog({self.event_name} | user={self.user_id} | sent={self.sent_to_posthog})"