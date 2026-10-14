"""
Management command: seed_combos

Loads org-curated Combos from the fixture file at:
  apps/combos/fixtures/curated_combos.json

For each combo in the fixture:
  - Skips it if a combo with the same title already exists (idempotent).
  - Creates the Combo by writing directly to the Combo model (system seed — no user context).
  - Attaches courses in order by resolving each course reference against
    the live database using provider + external_id, or title as a fallback.
  - Logs a warning for any course reference it cannot resolve so you know
    exactly which courses are missing from the DB after ingestion.

Usage:
  python manage.py seed_combos
  python manage.py seed_combos --dry-run
  python manage.py seed_combos --fixture path/to/other_file.json

The --dry-run flag prints what would be created without writing to the DB.
"""

import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.combos.models import Combo, ComboCourse
from apps.courses.models import Course

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE = (
    Path(__file__).resolve().parent.parent.parent  # apps/combos/
    / "fixtures"
    / "curated_combos.json"
)


class Command(BaseCommand):
    help = "Seed the database with org-curated Combos from a JSON fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            type=str,
            default=str(DEFAULT_FIXTURE),
            help="Path to the JSON fixture file (default: apps/combos/fixtures/curated_combos.json).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print what would be created without writing anything to the database.",
        )

    def handle(self, *args, **options):
        fixture_path = Path(options["fixture"])
        dry_run = options["dry_run"]

        if not fixture_path.exists():
            raise CommandError(f"Fixture file not found: {fixture_path}")

        self.stdout.write(f"Loading fixture: {fixture_path}")

        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                combos_data = json.load(f)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in fixture: {exc}") from exc

        if not isinstance(combos_data, list):
            raise CommandError("Fixture must be a JSON array of combo objects.")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN — nothing will be written to the database.\n")
            )

        created_count = 0
        skipped_count = 0
        warning_count = 0

        for i, combo_data in enumerate(combos_data, start=1):
            title = combo_data.get("title", f"[untitled at index {i}]")

            # ── Idempotency check ──────────────────────────────────────────────
            if Combo.objects.filter(title=title).exists():
                self.stdout.write(f"  SKIP  {title} (already exists)")
                skipped_count += 1
                continue

            # ── Resolve courses ────────────────────────────────────────────────
            course_refs = combo_data.get("courses", [])
            resolved_courses = []

            for ref in course_refs:
                course = self._resolve_course(ref)
                if course is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARN  [{title}] could not resolve course: {ref}"
                        )
                    )
                    warning_count += 1
                    logger.warning(
                        "seed_combos: unresolved course reference in combo '%s': %s",
                        title,
                        ref,
                    )
                else:
                    resolved_courses.append((course, ref))

            if dry_run:
                self.stdout.write(
                    f"  WOULD CREATE  {title} "
                    f"({len(resolved_courses)}/{len(course_refs)} courses resolved)"
                )
                continue

            # ── Create the Combo and attach courses ────────────────────────────
            try:
                with transaction.atomic():
                    combo = self._create_combo(combo_data)
                    self._attach_courses(combo, resolved_courses, course_refs)
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  ERROR  {title}: {exc}")
                )
                logger.error(
                    "seed_combos: failed to create combo '%s': %s",
                    title,
                    exc,
                    exc_info=True,
                )
                continue

            self.stdout.write(
                self.style.SUCCESS(
                    f"  CREATED  {title} "
                    f"({len(resolved_courses)}/{len(course_refs)} courses attached)"
                )
            )
            created_count += 1
            logger.info(
                "seed_combos: created combo '%s' with %d courses.",
                title,
                len(resolved_courses),
            )

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run complete. {len(combos_data)} combo(s) in fixture, "
                    f"{skipped_count} would be skipped, "
                    f"{warning_count} unresolved course reference(s)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. {created_count} created, {skipped_count} skipped, "
                    f"{warning_count} unresolved course reference(s) — check warnings above."
                )
            )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _resolve_course(self, ref: dict):
        """
        Attempt to find a Course in the database matching the given reference.

        Resolution order (most precise to least precise):
          1. provider + external_id  — exact match, preferred
          2. title                   — fallback for manually added courses
                                       (e.g. Khan Academy manual links)

        Returns the Course instance or None if no match is found.
        """
        # Strategy 1: provider + external_id (courses ingested via pipeline)
        provider = ref.get("provider")
        external_id = ref.get("external_id")

        if provider and external_id:
            course = Course.objects.filter(
                provider=provider,
                source_metadata__external_id=external_id,
            ).first()
            if course:
                return course

        # Strategy 2: title match (manually added courses, or pipeline courses
        # where the external_id wasn't known at fixture-authoring time)
        # FALLBACK: title lookup
        # PRIMARY: provider + external_id lookup above
        # CONDITION: provider or external_id missing from the fixture ref,
        #            or the course was added manually without a pipeline external_id
        # THRESHOLD: n/a — this is a data-authoring convenience, not a runtime path
        title = ref.get("title")
        if title:
            course = Course.objects.filter(title__iexact=title).first()
            if course:
                return course

        return None

    def _create_combo(self, data: dict):
        """
        Create a Combo by writing directly to the Combo model.

        WHY NOT ComboService.create_combo():
        ComboService.create_combo() requires a real User instance as its first
        argument and enforces user-specific business rules (private by default,
        no featuring, user email logging) that directly conflict with system
        seeding. Org-curated combos are public, featured, and have no owner.
        Calling the user-facing service here would require fabricating a dummy
        user or hacking around the rules it enforces — both wrong approaches.

        Direct model writes are permitted here because this management command
        IS the service layer for system-generated seed data. It is not a view,
        a task, or application code — it is a one-time administrative operation
        with its own validation (idempotency check, course resolution) already
        applied before this method is called.

        Rule 15 note: Rule 15 prohibits direct model writes in views and tasks.
        Management commands that act as their own orchestration layer are the
        documented exception — equivalent to how ingestion pipeline code writes
        courses directly via CourseIngestionService rather than the user API.

        The 'courses' key is intentionally excluded — course attachment is
        handled separately by _attach_courses() after the Combo is saved.
        """
        combo = Combo.objects.create(
            title=data["title"],
            short_description=data.get("short_description", ""),
            full_description=data.get("full_description", ""),
            overview=data.get("overview", ""),
            who_is_this_for=data.get("who_is_this_for", ""),
            learning_outcomes=data.get("learning_outcomes", []),
            prerequisites=data.get("prerequisites", []),
            skills_gained=data.get("skills_gained", []),
            learning_path_explanation=data.get("learning_path_explanation", ""),
            category=data.get("category", ""),
            sub_category=data.get("sub_category", ""),
            tags=data.get("tags", []),
            difficulty=data.get("difficulty", "Beginner"),
            recommended_age=data.get("recommended_age", "Adults"),
            estimated_weeks=data.get("estimated_weeks", 0),
            estimated_hours_per_week=data.get("estimated_hours_per_week", 0),
            is_public=data.get("is_public", True),
            is_featured=data.get("is_featured", False),
            created_by_type="system",
            created_by_user=None,
        )
        return combo

    def _attach_courses(self, combo, resolved_courses: list, original_refs: list):
        """
        Attach resolved courses to the Combo in the correct order.

        Order comes from the fixture's 'courses' array position (1-indexed).
        is_required and note are carried through from the fixture ref if present.

        Only resolved courses are attached. The caller already warned about
        unresolved ones, so this method is silent about missing entries.
        """
        for course, ref in resolved_courses:
            # Derive the 1-indexed order from the original refs list position.
            order = original_refs.index(ref) + 1
            ComboCourse.objects.create(
                combo=combo,
                course=course,
                order=order,
                is_required=ref.get("is_required", True),
                note=ref.get("note", ""),
            )