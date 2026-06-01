"""
Ingestion models.

IngestionLog — records every ingestion run: source, status, outcome, timing.

Required by Rule 8 (observability) and Rule 11 (fallback monitoring thresholds).
Every ingestion pipeline execution must produce an IngestionLog entry.
"""

import logging

from django.db import models

from common.models import TimestampedModel

logger = logging.getLogger(__name__)


class IngestionLog(TimestampedModel):
    """
    Audit log for every ingestion pipeline run.

    Records: which source, when it ran, how it went, what it did.
    FALLBACK status is set when a fallback path was triggered during ingestion.

    Rule 11: Fallback monitoring requires IngestionLog entries to be flagged
    when a fallback is triggered, enabling threshold tracking.
    """

    class Source(models.TextChoices):
        YOUTUBE = "youtube", "YouTube"
        FREECODECAMP = "freecodecamp", "freeCodeCamp"
        MIT_OCW = "mit_ocw", "MIT OpenCourseWare"
        OPENSTAX = "openstax", "OpenStax"
        CK12 = "ck12", "CK-12"

    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial Success"
        FALLBACK = "fallback", "Fallback Triggered"
        FAILED = "failed", "Failed"

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        help_text="Which external source this ingestion run pulled from.",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.STARTED,
        help_text="Outcome of the ingestion run.",
    )
    courses_fetched = models.PositiveIntegerField(
        default=0,
        help_text="Total raw courses retrieved from the source.",
    )
    courses_created = models.PositiveIntegerField(
        default=0,
        help_text="New courses written to the database in this run.",
    )
    courses_updated = models.PositiveIntegerField(
        default=0,
        help_text="Existing courses updated in this run.",
    )
    courses_skipped = models.PositiveIntegerField(
        default=0,
        help_text="Courses skipped (duplicate, invalid, or filtered out).",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error details if status is FAILED or PARTIAL.",
    )
    fallback_triggered = models.BooleanField(
        default=False,
        help_text=(
            "True when a fallback path was used during this run. "
            "Rule 11: 3 consecutive or 5 within 24h triggers investigation."
        ),
    )
    fallback_reason = models.TextField(
        blank=True,
        default="",
        help_text="Description of what caused the fallback, if fallback_triggered=True.",
    )
    started_at = models.DateTimeField(
        help_text="When this ingestion run began.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this ingestion run finished. Null if still running or failed mid-run.",
    )

    class Meta:
        verbose_name = "Ingestion Log"
        verbose_name_plural = "Ingestion Logs"
        db_table = "ingestion_logs"
        indexes = [
            models.Index(fields=["source", "status"], name="idx_ingestion_source_status"),
            models.Index(fields=["started_at"], name="idx_ingestion_started_at"),
            models.Index(fields=["fallback_triggered"], name="idx_ingestion_fallback"),
        ]
        ordering = ["-started_at"]

    def __str__(self):
        return f"IngestionLog({self.source} | {self.status} | {self.started_at})"