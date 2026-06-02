"""
Management command: flag_language_status

Runs the multi-layer language quality pipeline retroactively against all
existing courses in the database and updates language_status and
language_rejection_reason on each row.

This command is the one-time (and repeatable) mechanism for screening
courses that entered the database before the language pipeline was added
to the normalizer. It is also the right tool to re-screen courses after
tuning detection thresholds.

Usage:
    # Always dry-run first
    python manage.py flag_language_status --dry-run

    # Screen all active courses
    python manage.py flag_language_status

    # Screen one provider only
    python manage.py flag_language_status --provider YouTube

    # Re-screen courses already processed (override existing decisions)
    python manage.py flag_language_status --rescreen-all

    # Screen only courses still marked unknown
    python manage.py flag_language_status --unknown-only

Architecture note:
    This command writes directly to Course.objects.filter().update() for
    efficiency — running upsert_course() per row would be unnecessarily
    expensive for a retroactive scan. This is intentional and documented.
    The language pipeline logic itself lives in normalizer.LanguageDetector
    — this command only orchestrates the scan and writes the results.
"""

import logging
from collections import Counter

from django.core.management.base import BaseCommand

from apps.courses.models import Course
from apps.ingestion.normalizer import LanguageDetector

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Run the multi-layer language quality pipeline against existing courses "
        "and update language_status and language_rejection_reason."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show what would change without writing to the database.",
        )
        parser.add_argument(
            "--provider",
            type=str,
            default=None,
            help="Limit screening to one provider (e.g. YouTube, freeCodeCamp).",
        )
        parser.add_argument(
            "--unknown-only",
            action="store_true",
            default=False,
            help="Only screen courses with language_status=unknown (default behaviour).",
        )
        parser.add_argument(
            "--rescreen-all",
            action="store_true",
            default=False,
            help=(
                "Re-screen ALL active courses regardless of current language_status. "
                "WARNING: This will overwrite manually reviewed decisions. "
                "Use only after tuning detection thresholds."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        provider = options["provider"]
        unknown_only = options["unknown_only"]
        rescreen_all = options["rescreen_all"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN — nothing will be written to the database.\n"
                )
            )

        if rescreen_all and not dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: --rescreen-all will overwrite manually reviewed "
                    "language_status decisions. Proceeding in 3 seconds...\n"
                )
            )
            import time
            time.sleep(3)

        # ── Build queryset ─────────────────────────────────────────────────────
        qs = Course.objects.filter(is_active=True)

        if provider:
            qs = qs.filter(provider=provider)
            self.stdout.write(f"Filtering to provider: {provider}")

        if rescreen_all:
            self.stdout.write("Mode: re-screening ALL courses (ignoring current status)")
        else:
            # Default: only screen unknown courses so manual reviews are preserved
            qs = qs.filter(language_status=Course.LanguageStatus.UNKNOWN)
            self.stdout.write("Mode: screening UNKNOWN courses only")

        total = qs.count()
        self.stdout.write(f"Courses to screen: {total}\n")

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "No courses to screen. "
                    "Use --rescreen-all to re-screen previously processed courses."
                )
            )
            return

        # ── Run detection ──────────────────────────────────────────────────────
        detector = LanguageDetector()
        status_counts = Counter()
        flagged_courses = []
        rejected_courses = []
        errors = 0

        self.stdout.write("Screening courses...\n")

        for course in qs.iterator(chunk_size=100):
            try:
                description = course.short_description or course.full_description or ""

                # Extract audio_language from source_metadata for YouTube courses.
                # raw_payload['audio_language'] is defaultAudioLanguage from the
                # YouTube API — stored there by the updated youtube.py fetcher.
                # For existing courses ingested before the fetcher update, this
                # will be empty — the thin content and Lingua layers still apply.
                raw_payload = course.source_metadata.get("raw_payload", {}) or {}
                audio_language = raw_payload.get("audio_language", "") or ""

                result = detector.detect(
                    title=course.title,
                    description=description,
                    metadata_language=course.language,
                    audio_language=audio_language,
                )

                new_status = result["language_status"]
                new_reason = result["language_rejection_reason"]
                status_counts[new_status] += 1

                if new_status == Course.LanguageStatus.FLAGGED:
                    flagged_courses.append((course, result))
                elif new_status == Course.LanguageStatus.REJECTED:
                    rejected_courses.append((course, result))

                if not dry_run:
                    Course.objects.filter(pk=course.pk).update(
                        language_status=new_status,
                        language_rejection_reason=new_reason,
                    )

            except Exception as exc:
                errors += 1
                logger.error(
                    "flag_language_status: Error screening course '%s' [%s]: %s",
                    course.title,
                    course.pk,
                    exc,
                    exc_info=True,
                )
                self.stdout.write(
                    self.style.ERROR(f"  ERROR  {course.title[:80]}: {exc}")
                )

        # ── Print detailed reports ─────────────────────────────────────────────
        self._print_rejected_report(rejected_courses, dry_run)
        self._print_flagged_report(flagged_courses, dry_run)
        self._print_summary(
            total=total,
            status_counts=status_counts,
            errors=errors,
            dry_run=dry_run,
        )

        logger.info(
            "flag_language_status: Screening complete. "
            "total=%d accepted=%d flagged=%d rejected=%d errors=%d dry_run=%s",
            total,
            status_counts[Course.LanguageStatus.ACCEPTED],
            status_counts[Course.LanguageStatus.FLAGGED],
            status_counts[Course.LanguageStatus.REJECTED],
            errors,
            dry_run,
        )

    # ── Report helpers ─────────────────────────────────────────────────────────

    def _print_rejected_report(self, rejected_courses: list, dry_run: bool):
        """Print every rejected course with its reason."""
        if not rejected_courses:
            return

        action = "WOULD REJECT" if dry_run else "REJECTED"
        self.stdout.write(
            self.style.ERROR(f"\n{'─' * 60}")
        )
        self.stdout.write(
            self.style.ERROR(f"  {action} ({len(rejected_courses)} courses)")
        )
        self.stdout.write(
            self.style.ERROR(f"{'─' * 60}")
        )
        self.stdout.write(
            "  These courses will be hidden from the catalog.\n"
            "  Review in admin: /admin/courses/course/?language_status=rejected\n"
            "  To reinstate: set language_status to 'accepted' in the admin.\n"
        )

        for course, result in rejected_courses:
            self.stdout.write(
                self.style.ERROR(
                    f"  ✗  [{course.provider}] {course.title[:80]}"
                )
            )
            self.stdout.write(
                f"     Reason: {result['language_rejection_reason']}"
            )
            self.stdout.write(
                f"     Layers: {', '.join(result['layers_triggered'])}"
            )
            self.stdout.write(
                f"     Admin:  /admin/courses/course/{course.pk}/change/\n"
            )

    def _print_flagged_report(self, flagged_courses: list, dry_run: bool):
        """Print every flagged course with its reason and admin URL."""
        if not flagged_courses:
            return

        action = "WOULD FLAG" if dry_run else "FLAGGED"
        self.stdout.write(
            self.style.WARNING(f"\n{'─' * 60}")
        )
        self.stdout.write(
            self.style.WARNING(f"  {action} FOR REVIEW ({len(flagged_courses)} courses)")
        )
        self.stdout.write(
            self.style.WARNING(f"{'─' * 60}")
        )
        self.stdout.write(
            "  These courses are still visible but need human review.\n"
            "  Review in admin: /admin/courses/course/?language_status=flagged\n"
            "  For each: open the course, check the content, then set\n"
            "  language_status to 'accepted' or 'rejected' manually.\n"
        )

        for course, result in flagged_courses:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚑  [{course.provider}] {course.title[:80]}"
                )
            )
            self.stdout.write(
                f"     Reason: {result['language_rejection_reason']}"
            )
            self.stdout.write(
                f"     Layers: {', '.join(result['layers_triggered'])}"
            )
            self.stdout.write(
                f"     Admin:  /admin/courses/course/{course.pk}/change/\n"
            )

    def _print_summary(
        self,
        total: int,
        status_counts: Counter,
        errors: int,
        dry_run: bool,
    ):
        """Print the final summary counts."""
        accepted = status_counts[Course.LanguageStatus.ACCEPTED]
        flagged  = status_counts[Course.LanguageStatus.FLAGGED]
        rejected = status_counts[Course.LanguageStatus.REJECTED]
        prefix = "DRY RUN — " if dry_run else ""

        self.stdout.write(f"\n{'═' * 60}")
        self.stdout.write(f"  {prefix}SCREENING COMPLETE")
        self.stdout.write(f"{'═' * 60}")
        self.stdout.write(f"  Total screened : {total}")
        self.stdout.write(
            self.style.SUCCESS(f"  Accepted       : {accepted}")
        )
        self.stdout.write(
            self.style.WARNING(f"  Flagged        : {flagged}  ← needs human review")
        )
        self.stdout.write(
            self.style.ERROR(f"  Rejected       : {rejected}  ← hidden from catalog")
        )
        if errors:
            self.stdout.write(
                self.style.ERROR(f"  Errors         : {errors}  ← check logs")
            )
        self.stdout.write(f"{'═' * 60}\n")

        if flagged > 0:
            self.stdout.write(
                "Next step: review flagged courses at:\n"
                "  /admin/courses/course/?language_status=flagged\n"
            )
        if rejected > 0 and dry_run:
            self.stdout.write(
                "Run without --dry-run to apply these changes.\n"
            )