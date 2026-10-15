"""
Ingestion Celery tasks.

Defines the async tasks that trigger the ingestion pipeline.
Tasks are the only callers of pipeline.run_pipeline() from the async layer.

Task structure:
- run_ingestion_for_source(source_key) — runs one source, called by Beat schedule
- run_all_ingestion()                  — runs all sources in sequence (nightly batch)
- run_ingestion_manual(source_key)     — admin-triggered single-source run

Beat schedule is defined at the bottom of this file via INGESTION_BEAT_SCHEDULE.
To activate it, add to settings/base.py:

    from apps.ingestion.tasks import INGESTION_BEAT_SCHEDULE
    CELERY_BEAT_SCHEDULE = {**INGESTION_BEAT_SCHEDULE}

Rules enforced:
- Rule 3: Tasks call pipeline functions only — no direct DB writes
- Rule 6: Tasks contain no business logic — they dispatch to pipeline
- Rule 8: Every task logs its start, completion, and any failure
- Rule 14: One responsibility per task function
"""

import logging

from celery import shared_task
from celery.schedules import crontab
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Per-Source Task ──────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="ingestion.run_ingestion_for_source",
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_ingestion_for_source(self, source_key: str) -> dict:
    """
    Run the ingestion pipeline for a single source.

    This task is enqueued by the Celery Beat schedule (one task per source)
    and can also be called manually from admin or management commands.

    Args:
        source_key: IngestionLog.Source value e.g. 'youtube', 'freecodecamp'

    Returns:
        dict with run summary {source, status, created, updated, skipped, log_id}

    Rule 6: This task dispatches to run_pipeline() — no logic here.
    Rule 8: Start and completion are logged at INFO level.
    """
    from apps.ingestion.pipeline import run_pipeline

    logger.info(
        "run_ingestion_for_source: Task started. source=%s task_id=%s",
        source_key,
        self.request.id,
    )

    try:
        log = run_pipeline(source_key)

        result = {
            "source": source_key,
            "status": log.status,
            "created": log.courses_created,
            "updated": log.courses_updated,
            "skipped": log.courses_skipped,
            "log_id": str(log.pk),
            "fallback_triggered": log.fallback_triggered,
        }

        logger.info(
            "run_ingestion_for_source: Task complete. source=%s status=%s "
            "created=%d updated=%d skipped=%d",
            source_key,
            log.status,
            log.courses_created,
            log.courses_updated,
            log.courses_skipped,
        )

        return result

    except Exception as exc:
        logger.error(
            "run_ingestion_for_source: Task failed. source=%s error=%s. "
            "Retrying (attempt %d/%d).",
            source_key,
            exc,
            self.request.retries + 1,
            self.max_retries + 1,
        )
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


# ─── All-Sources Batch Task ───────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="ingestion.run_all_ingestion",
    max_retries=0,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=3600,
    soft_time_limit=3300,
)
def run_all_ingestion(self) -> dict:
    """
    Run the ingestion pipeline for ALL registered sources.

    Scheduled via CELERY_BEAT_SCHEDULE. A failure in one source does not
    stop the others.

    Rule 6: Dispatches to run_all_pipelines() — no logic here.
    Rule 8: Start, per-source completion, and final summary are logged.
    """
    from apps.ingestion.pipeline import SOURCE_REGISTRY, run_all_pipelines

    logger.info(
        "run_all_ingestion: Nightly batch started. sources=%s task_id=%s",
        list(SOURCE_REGISTRY.keys()),
        self.request.id,
    )

    try:
        logs = run_all_pipelines()

        results = {source: log.status for source, log in logs.items()}

        summary = {
            "completed": len(logs),
            "total": len(SOURCE_REGISTRY),
            "results": results,
            "started_at": timezone.now().isoformat(),
        }

        logger.info(
            "run_all_ingestion: Nightly batch complete. completed=%d/%d results=%s",
            len(logs),
            len(SOURCE_REGISTRY),
            results,
        )

        return summary

    except Exception as exc:
        logger.error(
            "run_all_ingestion: Batch failed with unhandled exception: %s",
            exc,
            exc_info=True,
        )
        raise


# ─── Manual Admin-Triggered Task ─────────────────────────────────────────────

@shared_task(
    bind=True,
    name="ingestion.run_ingestion_manual",
    max_retries=0,
    acks_late=True,
)
def run_ingestion_manual(self, source_key: str) -> dict:
    """
    Admin-triggered single-source ingestion run.

    max_retries=0 so admins get immediate failure feedback.
    Called from: Django admin custom actions or management commands.

    Rule 6: Dispatches to run_pipeline() — no logic here.
    """
    from apps.ingestion.pipeline import run_pipeline

    logger.info(
        "run_ingestion_manual: Manual run started. source=%s task_id=%s",
        source_key,
        self.request.id,
    )

    try:
        log = run_pipeline(source_key)

        result = {
            "source": source_key,
            "status": log.status,
            "created": log.courses_created,
            "updated": log.courses_updated,
            "skipped": log.courses_skipped,
            "log_id": str(log.pk),
        }

        logger.info(
            "run_ingestion_manual: Manual run complete. source=%s status=%s",
            source_key,
            log.status,
        )

        return result

    except Exception as exc:
        logger.error(
            "run_ingestion_manual: Manual run failed. source=%s error=%s",
            source_key,
            exc,
            exc_info=True,
        )
        raise


# ─── Celery Beat Schedule ─────────────────────────────────────────────────────
# Sources are staggered 15 minutes apart to avoid simultaneous external API calls.
#
# To activate, add to settings/base.py:
#
#   from apps.ingestion.tasks import INGESTION_BEAT_SCHEDULE
#   CELERY_BEAT_SCHEDULE = {**INGESTION_BEAT_SCHEDULE}

INGESTION_BEAT_SCHEDULE = {
    "ingest-youtube-nightly": {
        "task": "ingestion.run_ingestion_for_source",
        "schedule": crontab(hour=2, minute=0),
        "args": ["youtube"],
        "options": {"expires": 3600},
    },
    "ingest-freecodecamp-nightly": {
        "task": "ingestion.run_ingestion_for_source",
        "schedule": crontab(hour=2, minute=15),
        "args": ["freecodecamp"],
        "options": {"expires": 3600},
    },
    "ingest-mit-ocw-nightly": {
        "task": "ingestion.run_ingestion_for_source",
        "schedule": crontab(hour=2, minute=30),
        "args": ["mit_ocw"],
        "options": {"expires": 3600},
    },
    "ingest-openstax-nightly": {
        "task": "ingestion.run_ingestion_for_source",
        "schedule": crontab(hour=2, minute=45),
        "args": ["openstax"],
        "options": {"expires": 3600},
    },
    "ingest-ck12-nightly": {
        "task": "ingestion.run_ingestion_for_source",
        "schedule": crontab(hour=3, minute=0),
        "args": ["ck12"],
        "options": {"expires": 3600},
    },
}