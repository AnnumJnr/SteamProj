"""
Management command: ingest

Runs the ingestion pipeline for one source or all registered sources,
synchronously in the current process.

This is the deployment entry point for scheduled ingestion on Render:
a free-tier cron service runs `python manage.py ingest` daily. Unlike
the Celery Beat schedule (see apps/ingestion/tasks.py), it needs no
worker and no broker — the pipeline functions write to the database
directly. It is also the manual "refresh content now" tool for local
runs against a chosen settings module.

Usage:
    # All sources, in registry order
    python manage.py ingest

    # One source only
    python manage.py ingest --source youtube

    # Against production from a local machine (external DB URL vars)
    DB_HOST=... DB_PASSWORD=... PGSSLMODE=require \
        python manage.py ingest --settings=core.settings.production

Exit codes: 0 when at least one source finished (success/partial are
both acceptable outcomes); 1 when every attempted source failed — e.g.
YOUTUBE_API_KEY missing or no network — so the scheduler surfaces the
run as failed instead of silently doing nothing.

Rules enforced:
- Rule 6: Orchestration only — delegates to pipeline.run_pipeline() /
  pipeline.run_all_pipelines(), no business logic here.
- Rule 8: Per-source results are reported via the IngestionLog each
  run produces.
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.pipeline import (
    SOURCE_REGISTRY,
    run_all_pipelines,
    run_pipeline,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Run the ingestion pipeline synchronously: all registered sources, "
        "or one via --source. Used by the Render cron service for scheduled "
        "ingestion and available for manual content refreshes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            metavar="SOURCE_KEY",
            choices=sorted(SOURCE_REGISTRY.keys()),
            help=(
                "Run a single source only (e.g. youtube, openstax). "
                "Omit to run all registered sources in sequence."
            ),
        )

    def handle(self, *args, **options):
        if options["source"]:
            self._run_single(options["source"])
        else:
            self._run_all()

    # ─── Single Source ──────────────────────────────────────────────────────

    def _run_single(self, source_key: str) -> None:
        """Run one source; exit non-zero only on outright failure."""
        self.stdout.write(f"Running ingestion for source '{source_key}'...")

        log = run_pipeline(source_key)

        self._report(source_key, log)

        if log.status == "failed":
            raise CommandError(
                f"Ingestion for '{source_key}' failed. "
                f"See IngestionLog {log.pk} for details."
            )

    # ─── All Sources ────────────────────────────────────────────────────────

    def _run_all(self) -> None:
        """
        Run every registered source; a per-source failure does not stop
        the batch. Exit non-zero only when nothing succeeded at all.
        """
        total = len(SOURCE_REGISTRY)
        self.stdout.write(f"Running ingestion for all {total} sources...")

        logs = run_all_pipelines()

        for source_key in sorted(logs):
            self._report(source_key, logs[source_key])

        # run_all_pipelines() omits sources that raised entirely;
        # a returned log with status 'failed' counts as failed too.
        failed = [
            key
            for key in SOURCE_REGISTRY
            if key not in logs or logs[key].status == "failed"
        ]
        succeeded = total - len(failed)

        self.stdout.write(
            self.style.SUCCESS(
                f"Ingestion complete: {succeeded}/{total} sources finished."
            )
        )

        if failed:
            self.stdout.write(
                self.style.WARNING(f"Failed sources: {', '.join(sorted(failed))}")
            )

        if succeeded == 0:
            raise CommandError(
                "All ingestion sources failed — nothing was ingested."
            )

    # ─── Reporting ──────────────────────────────────────────────────────────

    def _report(self, source_key: str, log) -> None:
        """Print one source's outcome line from its IngestionLog."""
        style = (
            self.style.SUCCESS
            if log.status in ("success", "partial", "fallback")
            else self.style.ERROR
        )
        self.stdout.write(
            style(
                f"  {source_key}: {log.status} — "
                f"created={log.courses_created} "
                f"updated={log.courses_updated} "
                f"skipped={log.courses_skipped}"
            )
        )
