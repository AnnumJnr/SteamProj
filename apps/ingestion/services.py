"""
Ingestion services.

CourseIngestionService — all business logic for writing normalized courses
to the database. This is the only place in the ingestion pipeline that
touches the database (Rule 15).

IngestionLogService — all business logic for creating and updating
IngestionLog records (Rule 8 observability requirement).

Changes from Phase 3:
- upsert_course() now writes language_status and language_rejection_reason
  from NormalizedCourse to the Course row on both create and update paths.
- Update path no longer blindly resets is_active = True. A course that was
  manually set to is_active=False (e.g. dead YouTube link) stays inactive
  even when the pipeline re-encounters it. Only previously-active courses
  are kept active on update.
- language_status is NOT reset on update — a manually-reviewed and overridden
  status (e.g. admin changed flagged → accepted) is preserved across re-ingestion.
  Language status is only written on CREATE. On UPDATE it is left as-is so
  that human overrides are not silently reversed by the pipeline.

Rules enforced:
- Rule 1: All ingestion business logic lives here
- Rule 3: Pipeline calls services — never writes to DB directly
- Rule 8: Every significant action is logged
- Rule 15: All model writes go through service methods
- Rule 9: No hidden side effects — methods do what their names say
"""

import logging
from datetime import datetime, timezone

from django.db import IntegrityError, transaction

from apps.courses.models import Course
from apps.ingestion.models import IngestionLog
from apps.ingestion.normalizer import NormalizedCourse

logger = logging.getLogger(__name__)


class CourseIngestionService:
    """
    Handles all database writes for the ingestion pipeline.

    The core operation is upsert_course(): create a new Course if the
    external_id + provider combination does not exist, otherwise update
    the existing record with fresh data from the source.

    Rule 15: This is the ONLY place in the ingestion pipeline that calls
             Course.objects.create() or course.save().
    Rule 9: upsert_course() creates or updates a course and nothing else.
    """

    @staticmethod
    def upsert_course(normalized: NormalizedCourse) -> tuple[Course, bool]:
        """
        Create or update a Course from a NormalizedCourse.

        Returns: (course_instance, created: bool)
            created=True  → new course was inserted
            created=False → existing course was updated

        Lookup key: external_id stored in source_metadata + provider.

        CREATE behaviour:
          - All fields written from NormalizedCourse including language_status
            and language_rejection_reason set by the normalizer's language pipeline.

        UPDATE behaviour:
          - Mutable content fields are refreshed (title, description, thumbnail, etc.)
          - language_status and language_rejection_reason are NOT updated.
            Reason: a human may have manually reviewed and overridden the pipeline
            decision (e.g. changed flagged → accepted). Re-ingestion must not
            silently reverse that override. Language re-screening on existing courses
            is done explicitly via the flag_language_status management command.
          - is_active is NOT blindly reset to True on update. A course that was
            manually deactivated (e.g. dead link confirmed by a human) stays
            inactive. Only courses that were active before the update remain active.

        Rule 15: Only write path for ingestion.
        Rule 9: Creates/updates exactly one course. No events, no emails.
        Rule 13: Explicit — update_fields listed explicitly, not via **kwargs dump.
        """
        external_id = normalized.external_id
        provider = normalized.provider

        try:
            with transaction.atomic():
                existing = Course.objects.filter(
                    source_metadata__external_id=external_id,
                    provider=provider,
                ).first()

                if existing:
                    # ── UPDATE path ───────────────────────────────────────────
                    # Refresh content fields from the latest source data.
                    # Do NOT touch: language_status, language_rejection_reason,
                    # is_active (preserve human decisions on both).
                    existing.title = normalized.title
                    existing.short_description = normalized.short_description
                    existing.full_description = normalized.full_description
                    existing.instructor = normalized.instructor
                    existing.thumbnail_url = normalized.thumbnail_url
                    existing.category = normalized.category
                    existing.sub_category = normalized.sub_category
                    existing.level = normalized.level
                    existing.age_group = normalized.age_group
                    existing.format = normalized.format
                    existing.duration_hours = normalized.duration_hours
                    existing.duration_minutes = normalized.duration_minutes
                    existing.rating_average = normalized.rating_average
                    existing.rating_count = normalized.rating_count
                    existing.tags = normalized.tags
                    existing.learning_outcomes = normalized.learning_outcomes
                    existing.prerequisites = normalized.prerequisites
                    existing.is_free = normalized.is_free
                    existing.certificate_available = normalized.certificate_available
                    # language_status and language_rejection_reason intentionally
                    # omitted from update_fields — human overrides are preserved.
                    # is_active intentionally omitted — human deactivations preserved.

                    existing.save(update_fields=[
                        "title", "short_description", "full_description",
                        "instructor", "thumbnail_url", "category", "sub_category",
                        "level", "age_group", "format", "duration_hours",
                        "duration_minutes", "rating_average", "rating_count",
                        "tags", "learning_outcomes", "prerequisites",
                        "is_free", "certificate_available",
                        "updated_at",
                    ])

                    logger.debug(
                        "CourseIngestionService.upsert_course: Updated '%s' [%s / %s]",
                        normalized.title,
                        provider,
                        external_id,
                    )
                    return existing, False

                else:
                    # ── CREATE path ───────────────────────────────────────────
                    # All fields written including language_status and
                    # language_rejection_reason from the normalizer's pipeline.
                    course = Course.objects.create(
                        title=normalized.title,
                        short_description=normalized.short_description,
                        full_description=normalized.full_description,
                        source_url=normalized.source_url,
                        provider=normalized.provider,
                        provider_type=normalized.provider_type,
                        instructor=normalized.instructor,
                        thumbnail_url=normalized.thumbnail_url,
                        language=normalized.language,
                        category=normalized.category,
                        sub_category=normalized.sub_category,
                        level=normalized.level,
                        age_group=normalized.age_group,
                        format=normalized.format,
                        duration_hours=normalized.duration_hours,
                        duration_minutes=normalized.duration_minutes,
                        rating_average=normalized.rating_average,
                        rating_count=normalized.rating_count,
                        tags=normalized.tags,
                        learning_outcomes=normalized.learning_outcomes,
                        prerequisites=normalized.prerequisites,
                        is_free=normalized.is_free,
                        certificate_available=normalized.certificate_available,
                        source_metadata=normalized.source_metadata,
                        is_active=True,
                        # Language quality pipeline results
                        language_status=normalized.language_status,
                        language_rejection_reason=normalized.language_rejection_reason,
                    )

                    logger.debug(
                        "CourseIngestionService.upsert_course: Created '%s' "
                        "[%s / %s] language_status=%s",
                        normalized.title,
                        provider,
                        external_id,
                        normalized.language_status,
                    )
                    return course, True

        except IntegrityError as exc:
            logger.error(
                "CourseIngestionService.upsert_course: IntegrityError for "
                "'%s' [%s / %s]: %s",
                normalized.title,
                provider,
                external_id,
                exc,
            )
            raise

    @staticmethod
    def bulk_upsert_courses(
        normalized_courses: list[NormalizedCourse],
    ) -> dict[str, int]:
        """
        Upsert a list of NormalizedCourse objects.

        Returns a summary dict:
        {
            "created": int,
            "updated": int,
            "skipped": int,
        }

        Rule 14: One job — iterate and upsert. Counting is done here.
        Rule 8: Final counts are logged at INFO level by the caller (pipeline).
        """
        created = 0
        updated = 0
        skipped = 0

        for normalized in normalized_courses:
            try:
                _, was_created = CourseIngestionService.upsert_course(normalized)
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                logger.error(
                    "CourseIngestionService.bulk_upsert_courses: "
                    "Failed to upsert '%s': %s. Skipping.",
                    normalized.title,
                    exc,
                )
                skipped += 1

        return {"created": created, "updated": updated, "skipped": skipped}


class IngestionLogService:
    """
    Manages IngestionLog records throughout the lifecycle of an ingestion run.

    Rule 8: Observability — every run must have an IngestionLog entry.
    Rule 15: All IngestionLog writes go through this service.
    """

    @staticmethod
    def start_run(source: str) -> IngestionLog:
        """Create an IngestionLog entry to mark the start of a run."""
        log = IngestionLog.objects.create(
            source=source,
            status=IngestionLog.Status.STARTED,
            started_at=datetime.now(tz=timezone.utc),
        )
        logger.info(
            "IngestionLogService.start_run: Run started. source=%s log_id=%s",
            source,
            log.pk,
        )
        return log

    @staticmethod
    def complete_run(
        log: IngestionLog,
        courses_fetched: int,
        courses_created: int,
        courses_updated: int,
        courses_skipped: int,
        fallback_triggered: bool = False,
        fallback_reason: str = "",
    ) -> IngestionLog:
        """Mark an ingestion run as complete with final counts."""
        if fallback_triggered:
            status = IngestionLog.Status.FALLBACK
        elif courses_skipped > 0 and courses_created + courses_updated == 0:
            status = IngestionLog.Status.FAILED
        elif courses_skipped > 0:
            status = IngestionLog.Status.PARTIAL
        else:
            status = IngestionLog.Status.SUCCESS

        log.status = status
        log.courses_fetched = courses_fetched
        log.courses_created = courses_created
        log.courses_updated = courses_updated
        log.courses_skipped = courses_skipped
        log.fallback_triggered = fallback_triggered
        log.fallback_reason = fallback_reason
        log.completed_at = datetime.now(tz=timezone.utc)

        log.save(update_fields=[
            "status", "courses_fetched", "courses_created", "courses_updated",
            "courses_skipped", "fallback_triggered", "fallback_reason",
            "completed_at",
        ])

        logger.info(
            "IngestionLogService.complete_run: Run complete. "
            "source=%s status=%s created=%d updated=%d skipped=%d fallback=%s",
            log.source, status, courses_created, courses_updated,
            courses_skipped, fallback_triggered,
        )
        return log

    @staticmethod
    def fail_run(log: IngestionLog, error_message: str) -> IngestionLog:
        """Mark an ingestion run as failed with an error message."""
        log.status = IngestionLog.Status.FAILED
        log.error_message = str(error_message)[:2000]
        log.completed_at = datetime.now(tz=timezone.utc)
        log.save(update_fields=["status", "error_message", "completed_at"])

        logger.error(
            "IngestionLogService.fail_run: Run failed. source=%s error=%s",
            log.source,
            error_message,
        )
        return log