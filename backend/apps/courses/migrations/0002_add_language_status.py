"""
Migration: Add language_status and language_rejection_reason to courses table.

Generated for: apps/courses
Depends on: the last migration in your courses app (check with
            python manage.py showmigrations courses and update
            the dependencies tuple below to match your last migration number).

HOW TO USE:
1. Find your latest courses migration:
       python manage.py showmigrations courses
   The last entry (marked [X]) is your dependency.

2. Rename this file to match the next number in sequence.
   Example: if your last migration is 0003_..., rename this to
            0004_add_language_status.py

3. Update the dependencies list below to reference your actual last migration.

4. Place the file in: apps/courses/migrations/

5. Run: python manage.py migrate

DO NOT run makemigrations after placing this file — it is the migration.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    # ── UPDATE THIS to match your last courses migration ──────────────────────
    # Example: ("courses", "0003_alter_course_something")
    # Run `python manage.py showmigrations courses` to find the right value.
    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        # Add language_status field
        migrations.AddField(
            model_name="course",
            name="language_status",
            field=models.CharField(
                choices=[
                    ("unknown",  "Unknown"),
                    ("accepted", "Accepted"),
                    ("flagged",  "Flagged"),
                    ("rejected", "Rejected"),
                ],
                default="unknown",
                max_length=10,
                help_text=(
                    "Result of the multi-layer language quality pipeline. "
                    "unknown: not yet checked. "
                    "accepted: confirmed English. "
                    "flagged: uncertain, held for human review (still visible). "
                    "rejected: confident non-English, hidden from catalog."
                ),
            ),
        ),

        # Add language_rejection_reason field
        migrations.AddField(
            model_name="course",
            name="language_rejection_reason",
            field=models.CharField(
                blank=True,
                default="",
                max_length=300,
                help_text=(
                    "Why this course was flagged or rejected by the language pipeline. "
                    "Empty for accepted and unknown courses."
                ),
            ),
        ),

        # Add index on language_status for fast admin filtering
        migrations.AddIndex(
            model_name="course",
            index=models.Index(
                fields=["language_status"],
                name="idx_course_language_status",
            ),
        ),
    ]