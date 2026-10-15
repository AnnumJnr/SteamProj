"""
Analytics Celery tasks.

Handles async delivery of EventLog records to PostHog.

Rule 8 (observability):
- Every PostHog delivery attempt is logged
- EventLog.sent_to_posthog is updated on success
- EventLog.posthog_error is updated on failure
- sent_to_posthog=False records are the replay mechanism

Rule 9 (no hidden side effects):
- This task delivers to PostHog and updates EventLog — nothing else
- No email sending, no profile updates

PostHog HTTP API used directly (not the posthog-python SDK) to avoid adding
a dependency. The capture endpoint is a simple POST with the API key.
If the PostHog SDK is added later, replace _send_to_posthog() only —
the task structure stays the same.

Call chain:
    AnalyticsService.fire_event()
        → dispatch_event_to_posthog_task.delay(event_log_id)
            → _send_to_posthog()
            → EventLog updated
"""

import logging

import requests as http_requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# PostHog capture endpoint
POSTHOG_CAPTURE_URL = "https://app.posthog.com/capture/"

# Timeout for PostHog HTTP requests (seconds)
POSTHOG_REQUEST_TIMEOUT = 10


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,    # seconds — increases per retry via exponential backoff below
    name="analytics.dispatch_event_to_posthog",
)
def dispatch_event_to_posthog_task(self, event_log_id: int) -> dict:
    """
    Deliver a single EventLog record to PostHog.

    Fetches the EventLog by ID, sends it to the PostHog capture API,
    and updates EventLog.sent_to_posthog on success.

    On failure: retries up to 5 times with exponential backoff.
    If all retries are exhausted: EventLog.posthog_error is set.
    The record remains queryable via EventLog.objects.filter(sent_to_posthog=False)
    for manual replay via AnalyticsService.replay_failed_events().

    Args:
        event_log_id: Primary key of the EventLog record to deliver.

    Returns:
        dict with delivery status and event_log_id.
    """
    from apps.analytics.models import EventLog

    # ── Fetch the EventLog record ─────────────────────────────────────────────
    try:
        event_log = EventLog.objects.get(pk=event_log_id)
    except EventLog.DoesNotExist:
        logger.error(
            "dispatch_event_to_posthog_task: EventLog id=%s not found. "
            "Cannot deliver to PostHog.",
            event_log_id,
        )
        return {"status": "not_found", "event_log_id": event_log_id}

    # Skip if already sent (handles duplicate task dispatch edge cases)
    if event_log.sent_to_posthog:
        logger.info(
            "dispatch_event_to_posthog_task: EventLog id=%s already sent. Skipping.",
            event_log_id,
        )
        return {"status": "already_sent", "event_log_id": event_log_id}

    # ── Check PostHog API key ─────────────────────────────────────────────────
    api_key = getattr(settings, "POSTHOG_API_KEY", "")
    if not api_key:
        logger.warning(
            "dispatch_event_to_posthog_task: POSTHOG_API_KEY is not configured. "
            "EventLog id=%s recorded locally but not sent to PostHog. "
            "Set POSTHOG_API_KEY in .env to enable PostHog delivery.",
            event_log_id,
        )
        # Mark as a configuration-level skip — not a delivery failure.
        # Do not update sent_to_posthog so the record remains replayable
        # once the key is configured.
        return {"status": "no_api_key", "event_log_id": event_log_id}

    # ── Attempt PostHog delivery ──────────────────────────────────────────────
    posthog_host = getattr(settings, "POSTHOG_HOST", POSTHOG_CAPTURE_URL)
    capture_url = f"{posthog_host.rstrip('/')}/capture/"

    # PostHog capture payload structure
    payload = {
        "api_key": api_key,
        "event": event_log.event_name,
        "distinct_id": event_log.user_id if event_log.user_id else "anonymous",
        "timestamp": event_log.fired_at.isoformat(),
        "properties": {
            **event_log.properties,
            "$lib": "stem-platform-backend",
        },
    }

    logger.info(
        "dispatch_event_to_posthog_task: Sending event='%s' user='%s' "
        "EventLog id=%s (attempt %s/%s)",
        event_log.event_name,
        event_log.user_id or "anonymous",
        event_log_id,
        self.request.retries + 1,
        self.max_retries + 1,
    )

    try:
        response = http_requests.post(
            capture_url,
            json=payload,
            timeout=POSTHOG_REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        # ── Success — update EventLog ─────────────────────────────────────────
        EventLog.objects.filter(pk=event_log_id).update(
            sent_to_posthog=True,
            posthog_error="",
        )
        logger.info(
            "dispatch_event_to_posthog_task: Successfully delivered event='%s' "
            "EventLog id=%s to PostHog.",
            event_log.event_name,
            event_log_id,
        )
        return {"status": "sent", "event_log_id": event_log_id}

    except http_requests.exceptions.Timeout as exc:
        error_msg = f"PostHog request timed out after {POSTHOG_REQUEST_TIMEOUT}s"
        return _handle_delivery_failure(self, event_log_id, event_log.event_name, error_msg, exc)

    except http_requests.exceptions.HTTPError as exc:
        error_msg = f"PostHog HTTP error: {exc.response.status_code} {exc.response.text[:200]}"
        return _handle_delivery_failure(self, event_log_id, event_log.event_name, error_msg, exc)

    except http_requests.exceptions.RequestException as exc:
        error_msg = f"PostHog request failed: {str(exc)}"
        return _handle_delivery_failure(self, event_log_id, event_log.event_name, error_msg, exc)


def _handle_delivery_failure(self, event_log_id: int, event_name: str, error_msg: str, exc: Exception) -> dict:
    """
    Handle a failed PostHog delivery attempt.

    Updates EventLog.posthog_error with the failure reason, then retries
    the task with exponential backoff. If max_retries is exhausted, logs
    a final error — the EventLog record remains for manual replay.

    Exponential backoff: retry_delay = default_retry_delay * 2^retry_count
    Retry delays: 30s, 60s, 120s, 240s, 480s (if max_retries=5)

    Args:
        self:          The bound Celery task instance.
        event_log_id:  EventLog PK.
        event_name:    Event name string (for logging).
        error_msg:     Human-readable failure description.
        exc:           The original exception.
    """
    from apps.analytics.models import EventLog

    # Record the error on the EventLog
    EventLog.objects.filter(pk=event_log_id).update(posthog_error=error_msg[:500])

    retry_count = self.request.retries
    max_retries = self.max_retries

    if retry_count < max_retries:
        # Exponential backoff
        countdown = self.default_retry_delay * (2 ** retry_count)
        logger.warning(
            "dispatch_event_to_posthog_task: Delivery failed for EventLog id=%s "
            "event='%s': %s. Retry %s/%s in %ss.",
            event_log_id,
            event_name,
            error_msg,
            retry_count + 1,
            max_retries,
            countdown,
        )
        raise self.retry(exc=exc, countdown=countdown)
    else:
        # All retries exhausted
        logger.error(
            "dispatch_event_to_posthog_task: All %s retries exhausted for "
            "EventLog id=%s event='%s'. Final error: %s. "
            "Record remains in EventLog for manual replay via "
            "AnalyticsService.replay_failed_events().",
            max_retries,
            event_log_id,
            event_name,
            error_msg,
        )
        return {"status": "failed_permanently", "event_log_id": event_log_id}