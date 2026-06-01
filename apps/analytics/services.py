"""
Analytics services.

Central event dispatch logic for all backend-fired analytics events.

Rule 3: Services are the entry point for analytics business logic.
Rule 7: Every event has one authoritative emitter — enforced via BACKEND_EVENTS validation.
Rule 8: All events are persisted to EventLog before async dispatch to PostHog.
         If PostHog is unavailable, the EventLog record enables replay.
Rule 9: fire_event() creates an EventLog and queues a task — nothing else.
Rule 14: Each method has exactly one job.

Call chain:
    View/Service → AnalyticsService.fire_event()
        → EventLog created (local backup)
        → dispatch_event_to_posthog_task.delay(event_log_id)
            → PostHog HTTP call
            → EventLog.sent_to_posthog updated
"""

import logging
from typing import Any

from django.utils import timezone

from apps.analytics.events import BACKEND_EVENTS

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Dispatches analytics events for backend-owned interactions.

    Only fires events listed in BACKEND_EVENTS (analytics/events.py).
    Frontend-owned events (COURSE_VIEWED, COMBO_VIEWED, etc.) are fired
    by the frontend directly — the backend never fires them.
    """

    @staticmethod
    def fire_event(
        event_name: str,
        user_id: str = "",
        properties: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Record an analytics event locally and dispatch it to PostHog asynchronously.

        Steps:
        1. Validate that the event is a known backend event (Rule 7)
        2. Create an EventLog record (Rule 8 — local backup before async delivery)
        3. Dispatch the PostHog delivery task (non-blocking)

        Args:
            event_name: Must be a constant from analytics/events.py.
            user_id:    String UUID of the user. Empty string for anonymous events.
            properties: Event-specific payload dict. Optional.
            context:    Platform context (device, country, etc.). Optional.
                        Defaults to {"platform": "web"} if not provided.

        Rule 9: This function creates an EventLog and queues a task. Nothing else.
        No email sending, no profile updates, no other side effects.
        """
        # ── Validate event name ───────────────────────────────────────────────
        if event_name not in BACKEND_EVENTS:
            logger.warning(
                "AnalyticsService.fire_event: Attempted to fire unknown or "
                "frontend-owned event '%s'. Skipping. "
                "Check analytics/events.py — only BACKEND_EVENTS may be fired here.",
                event_name,
            )
            return

        properties = properties or {}
        context = context or {"platform": "web"}

        # ── Create local EventLog record ──────────────────────────────────────
        # Import here to avoid circular imports at module load time.
        from apps.analytics.models import EventLog

        try:
            event_log = EventLog.objects.create(
                event_name=event_name,
                user_id=user_id,
                properties=properties,
                context=context,
                sent_to_posthog=False,
            )
            logger.info(
                "AnalyticsService.fire_event: EventLog created — "
                "event='%s' user='%s' log_id=%s",
                event_name,
                user_id or "anonymous",
                event_log.pk,
            )
        except Exception:
            # If EventLog creation fails, log and abort — do not dispatch to PostHog
            # without a local record, as we'd lose replay capability.
            logger.error(
                "AnalyticsService.fire_event: Failed to create EventLog for "
                "event='%s' user='%s'. Event not dispatched to PostHog.",
                event_name,
                user_id or "anonymous",
                exc_info=True,
            )
            return

        # ── Dispatch async PostHog delivery ───────────────────────────────────
        # Import task here to avoid circular imports.
        from apps.analytics.tasks import dispatch_event_to_posthog_task

        try:
            dispatch_event_to_posthog_task.delay(event_log.pk)
            logger.info(
                "AnalyticsService.fire_event: PostHog dispatch task queued "
                "for EventLog id=%s",
                event_log.pk,
            )
        except Exception:
            # Task queuing failed (e.g. broker unavailable).
            # The EventLog record exists — event can be replayed later via
            # EventLog.objects.filter(sent_to_posthog=False).
            logger.error(
                "AnalyticsService.fire_event: Failed to queue PostHog dispatch "
                "task for EventLog id=%s. Event is recorded locally and can be replayed.",
                event_log.pk,
                exc_info=True,
            )

    @staticmethod
    def replay_failed_events(limit: int = 100) -> int:
        """
        Re-dispatch all EventLog records that were not successfully sent to PostHog.

        Intended for use in a management command or admin action — not called
        automatically. Provides manual recovery when PostHog was unavailable.

        Args:
            limit: Maximum number of events to replay in one call. Default 100.

        Returns:
            Number of events queued for replay.

        Rule 8: EventLog.sent_to_posthog=False is the replay mechanism.
        """
        from apps.analytics.models import EventLog
        from apps.analytics.tasks import dispatch_event_to_posthog_task

        unsent = EventLog.objects.filter(sent_to_posthog=False)[:limit]
        count = 0

        for event_log in unsent:
            try:
                dispatch_event_to_posthog_task.delay(event_log.pk)
                count += 1
            except Exception:
                logger.error(
                    "AnalyticsService.replay_failed_events: Failed to queue "
                    "replay for EventLog id=%s",
                    event_log.pk,
                    exc_info=True,
                )

        logger.info(
            "AnalyticsService.replay_failed_events: Queued %s events for replay.",
            count,
        )
        return count