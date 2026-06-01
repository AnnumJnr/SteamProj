"""
Ingestion pipeline orchestrator.

Coordinates the full ingestion flow for a single source:
    fetch → normalize → upsert → log

This file is the only place that wires all three layers together.
Views, tasks, and management commands call run_pipeline() — they do not
call fetchers, normalizers, or services directly.

Rules enforced:
- Rule 1: Orchestration logic lives here, not in tasks or views
- Rule 3: Pipeline calls services for all DB writes
- Rule 8: Every stage is logged; IngestionLog is updated throughout
- Rule 14: Each function has one job — orchestration is separated from execution
- Rule 2: Fallbacks are explicit and logged
"""

import logging

from apps.ingestion.models import IngestionLog
from apps.ingestion.normalizer import CourseNormalizer
from apps.ingestion.services import CourseIngestionService, IngestionLogService
from apps.ingestion.sources.base import BaseIngestionSource, FetchResult
from apps.ingestion.sources.ck12 import Ck12IngestionSource
from apps.ingestion.sources.freecodecamp import FreecodeCAmpIngestionSource
from apps.ingestion.sources.mit_ocw import MitOcwIngestionSource
from apps.ingestion.sources.openStax import OpenStaxIngestionSource
from apps.ingestion.sources.youtube import YouTubeIngestionSource

logger = logging.getLogger(__name__)


# ─── Source Registry ──────────────────────────────────────────────────────────
# Maps IngestionLog.Source values to their source class.
# Rule 13: Explicit registry — no dynamic class discovery.

SOURCE_REGISTRY: dict[str, type[BaseIngestionSource]] = {
    IngestionLog.Source.YOUTUBE: YouTubeIngestionSource,
    IngestionLog.Source.FREECODECAMP: FreecodeCAmpIngestionSource,
    IngestionLog.Source.MIT_OCW: MitOcwIngestionSource,
    IngestionLog.Source.OPENSTAX: OpenStaxIngestionSource,
    IngestionLog.Source.CK12: Ck12IngestionSource,
}


# ─── Pipeline Entry Point ─────────────────────────────────────────────────────

def run_pipeline(source_key: str) -> IngestionLog:
    """
    Execute the full ingestion pipeline for one source.

    This is the single entry point called by Celery tasks and management commands.
    It coordinates: start log → fetch → normalize → upsert → complete log.

    Returns the completed IngestionLog for the run.

    Rule 3: Calls services for all DB operations.
    Rule 8: IngestionLog is created at start and updated at every significant stage.
    Rule 14: Delegates fetch, normalize, upsert to dedicated functions.

    Args:
        source_key: One of IngestionLog.Source values
                    e.g. 'youtube', 'freecodecamp', 'mit_ocw', 'openstax', 'ck12'
    """
    logger.info("run_pipeline: Starting pipeline for source='%s'", source_key)

    # ── Validate source key ──
    if source_key not in SOURCE_REGISTRY:
        logger.error(
            "run_pipeline: Unknown source_key='%s'. Valid keys: %s",
            source_key,
            list(SOURCE_REGISTRY.keys()),
        )
        raise ValueError(f"Unknown ingestion source: '{source_key}'")

    # ── Step 1: Start IngestionLog ──
    log = IngestionLogService.start_run(source=source_key)

    try:
        # ── Step 2: Fetch raw data ──
        fetch_result = _fetch(source_key)

        if not fetch_result.success:
            return IngestionLogService.fail_run(
                log=log,
                error_message=fetch_result.error_message or "Fetch returned success=False",
            )

        logger.info(
            "run_pipeline: Fetch complete. source=%s raw_count=%d courses=%d",
            source_key,
            fetch_result.raw_count,
            len(fetch_result.courses),
        )

        # ── Step 3: Normalize raw courses ──
        normalized_courses = _normalize(fetch_result)

        logger.info(
            "run_pipeline: Normalization complete. source=%s normalized=%d (of %d raw)",
            source_key,
            len(normalized_courses),
            len(fetch_result.courses),
        )

        skipped_in_normalization = len(fetch_result.courses) - len(normalized_courses)

        # ── Step 4: Upsert to database ──
        upsert_summary = _upsert(normalized_courses)

        logger.info(
            "run_pipeline: Upsert complete. source=%s created=%d updated=%d skipped=%d",
            source_key,
            upsert_summary["created"],
            upsert_summary["updated"],
            upsert_summary["skipped"],
        )

        # ── Step 5: Complete IngestionLog ──
        total_skipped = skipped_in_normalization + upsert_summary["skipped"]

        completed_log = IngestionLogService.complete_run(
            log=log,
            courses_fetched=fetch_result.raw_count,
            courses_created=upsert_summary["created"],
            courses_updated=upsert_summary["updated"],
            courses_skipped=total_skipped,
            fallback_triggered=fetch_result.fallback_triggered,
            fallback_reason=fetch_result.fallback_reason,
        )

        return completed_log

    except Exception as exc:
        # Unrecoverable error — mark run as failed and re-raise so Celery retries
        logger.error(
            "run_pipeline: Unrecoverable error for source='%s': %s",
            source_key,
            exc,
            exc_info=True,
        )
        IngestionLogService.fail_run(log=log, error_message=str(exc))
        raise


# ─── Stage Functions ──────────────────────────────────────────────────────────
# Each function is one pipeline stage with one responsibility.
# Rule 14: One job per function.

def _fetch(source_key: str) -> FetchResult:
    """
    Stage 1: Instantiate the source and fetch raw data.

    Rule 14: Fetching only. Returns FetchResult.
    Rule 9: No DB access here.
    """
    source_class = SOURCE_REGISTRY[source_key]
    source = source_class()

    logger.debug("_fetch: Calling %s.fetch()", source_class.__name__)
    return source.fetch()


def _normalize(fetch_result: FetchResult) -> list:
    """
    Stage 2: Normalize all raw courses from the fetch result.

    Skips courses that fail normalization (returns None from normalizer).
    Logs a warning for each skipped course.

    Rule 14: Normalization only. Returns list of NormalizedCourse.
    Rule 9: No DB access here.
    """
    normalizer = CourseNormalizer()
    normalized = []

    for raw_course in fetch_result.courses:
        try:
            result = normalizer.normalize(raw_course)
            if result is not None:
                normalized.append(result)
            else:
                logger.warning(
                    "_normalize: Normalizer returned None for external_id='%s' title='%s'. "
                    "Course skipped.",
                    raw_course.external_id,
                    raw_course.title,
                )
        except Exception as exc:
            logger.error(
                "_normalize: Unexpected error normalizing external_id='%s': %s. Skipping.",
                raw_course.external_id,
                exc,
            )

    return normalized


def _upsert(normalized_courses: list) -> dict[str, int]:
    """
    Stage 3: Write all normalized courses to the database.

    Delegates to CourseIngestionService.bulk_upsert_courses().
    Returns the summary dict {created, updated, skipped}.

    Rule 3: All DB writes go through the service layer.
    Rule 14: Upsert only. Returns counts.
    """
    if not normalized_courses:
        logger.warning("_upsert: No normalized courses to write.")
        return {"created": 0, "updated": 0, "skipped": 0}

    return CourseIngestionService.bulk_upsert_courses(normalized_courses)


# ─── Convenience: Run All Sources ─────────────────────────────────────────────

def run_all_pipelines() -> dict[str, IngestionLog]:
    """
    Run the full ingestion pipeline for every registered source.

    Used by the nightly batch Celery task. Each source runs independently —
    a failure in one source does not stop the others.

    Returns a dict of {source_key: IngestionLog} for each run.

    Rule 8: Each source produces its own IngestionLog.
    Rule 14: Orchestration only — delegates to run_pipeline() for each source.
    """
    results: dict[str, IngestionLog] = {}

    for source_key in SOURCE_REGISTRY:
        try:
            log = run_pipeline(source_key)
            results[source_key] = log
            logger.info(
                "run_all_pipelines: Completed source='%s' status='%s'",
                source_key,
                log.status,
            )
        except Exception as exc:
            # Per-source failure is non-fatal for the batch — other sources continue
            # FALLBACK: Skip failed source, continue with remaining sources in batch
            # PRIMARY: apps/ingestion/pipeline.py → run_pipeline()
            # CONDITION: run_pipeline() raises an unrecoverable exception for one source
            # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → investigate primary
            logger.error(
                "run_all_pipelines: Source '%s' failed with unhandled exception: %s. "
                "Continuing with remaining sources.",
                source_key,
                exc,
            )

    logger.info(
        "run_all_pipelines: All sources attempted. Completed=%d/%d",
        len(results),
        len(SOURCE_REGISTRY),
    )

    return results