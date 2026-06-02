"""
Course model.

Represents a single course sourced from an external provider.
All courses are ingested (YouTube, freeCodeCamp, MIT OCW, OpenStax, CK-12)
or manually added (Khan Academy).

source_metadata stores the original data from the provider, enabling
reprocessing and attribution compliance.

Changes from Phase 1:
- Added LanguageStatus choice class
- Added language_status field (replaces sole use of is_active for language filtering)
- Added language_rejection_reason field (audit trail for detection decisions)
 
These two fields separate moderation state from visibility state — is_active
means the course exists on its source platform; language_status means the
course has passed the language quality gate. They are orthogonal concerns.
"""
 
import logging
 
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
 
from common.models import TimestampedModel
 
logger = logging.getLogger(__name__)
 
 
class Course(TimestampedModel):
    """
    Core course entity.
 
    Taxonomy follows the STEM categories defined in Section 8 of the master reference:
    Computer Science | Mathematics | Natural Sciences | Engineering |
    Technology & Applied Skills | STEM Foundations
    """
 
    # ─── Provider Choices ────────────────────────────────────────────────────
 
    class Provider(models.TextChoices):
        YOUTUBE = "YouTube", "YouTube"
        FREECODECAMP = "freeCodeCamp", "freeCodeCamp"
        MIT_OCW = "MIT OCW", "MIT OpenCourseWare"
        OPENSTAX = "OpenStax", "OpenStax"
        CK12 = "CK-12", "CK-12"
        KHAN_ACADEMY = "Khan Academy", "Khan Academy"
 
    class ProviderType(models.TextChoices):
        VIDEO_PLATFORM = "video_platform", "Video Platform"
        LEARNING_PLATFORM = "learning_platform", "Learning Platform"
        UNIVERSITY = "university", "University"
        OPEN_TEXTBOOK = "open_textbook", "Open Textbook"
 
    # ─── Content Classification Choices ──────────────────────────────────────
 
    class Level(models.TextChoices):
        BEGINNER = "Beginner", "Beginner"
        INTERMEDIATE = "Intermediate", "Intermediate"
        ADVANCED = "Advanced", "Advanced"
 
    class AgeGroup(models.TextChoices):
        KIDS = "Kids", "Kids (under 13)"
        TEENS = "Teens", "Teens (13–17)"
        ADULTS = "Adults", "Adults (18--)"
 
    class Format(models.TextChoices):
        VIDEO = "Video", "Video"
        TEXT = "Text", "Text"
        INTERACTIVE = "Interactive", "Interactive"
 
    # ─── STEM Category Choices ────────────────────────────────────────────────
    # Top-level categories from Section 8 of the master reference.
 
    class Category(models.TextChoices):
        COMPUTER_SCIENCE = "Computer Science", "Computer Science"
        MATHEMATICS = "Mathematics", "Mathematics"
        NATURAL_SCIENCES = "Natural Sciences", "Natural Sciences"
        ENGINEERING = "Engineering", "Engineering"
        TECHNOLOGY_APPLIED = "Technology & Applied Skills", "Technology & Applied Skills"
        STEM_FOUNDATIONS = "STEM Foundations", "STEM Foundations"
 
    # ─── Language Status Choices ──────────────────────────────────────────────
    # Tracks the outcome of the multi-layer language quality pipeline.
    # Kept separate from is_active deliberately:
    #   is_active     = does this course still exist on its source platform?
    #   language_status = has this course passed the English quality gate?
    # These are orthogonal states. Mixing them makes debugging impossible.
 
    class LanguageStatus(models.TextChoices):
        UNKNOWN  = "unknown",  "Unknown"   # Not yet run through the pipeline
        ACCEPTED = "accepted", "Accepted"  # Confirmed English — visible in catalog
        FLAGGED  = "flagged",  "Flagged"   # Uncertain — held for human review, still visible
        REJECTED = "rejected", "Rejected"  # Confident non-English — hidden from catalog
 
    # ─── Core Fields ─────────────────────────────────────────────────────────
 
    title = models.CharField(
        max_length=500,
        help_text="Course title as displayed on the platform.",
    )
    short_description = models.TextField(
        blank=True,
        default="",
        max_length=300,
        help_text="Short summary shown in course cards (max 500 chars).",
    )
    full_description = models.TextField(
        blank=True,
        default="",
        help_text="Full course description shown on the detail page.",
    )
    learning_outcomes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of what learners will achieve e.g. ['Understand variables', 'Write loops'].",
    )
    prerequisites = models.JSONField(
        default=list,
        blank=True,
        help_text="List of prerequisite knowledge or courses.",
    )
 
    # ─── Provider Info ────────────────────────────────────────────────────────
 
    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
        help_text="The external platform or institution that created this course.",
    )
    provider_type = models.CharField(
        max_length=50,
        choices=ProviderType.choices,
        help_text="Category of provider.",
    )
    source_url = models.URLField(
        help_text="Canonical URL to the course on the source platform.",
    )
    instructor = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Name of the course instructor or creator.",
    )
 
    # ─── Taxonomy ─────────────────────────────────────────────────────────────
 
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        help_text="Top-level STEM category. Drives filtering and Combo grouping.",
    )
    sub_category = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="More specific sub-category within the top-level category.",
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Free-form tags for search and filtering e.g. ['python', 'loops', 'beginner'].",
    )
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER,
    )
    age_group = models.CharField(
        max_length=10,
        choices=AgeGroup.choices,
        default=AgeGroup.ADULTS,
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text="ISO 639-1 language code e.g. 'en', 'fr'. Note: not reliable alone — "
                  "use language_status for filtering decisions.",
    )
    format = models.CharField(
        max_length=20,
        choices=Format.choices,
        default=Format.VIDEO,
    )
 
    # ─── Duration ─────────────────────────────────────────────────────────────
 
    duration_hours = models.PositiveIntegerField(
        default=0,
        help_text="Total course duration in hours.",
    )
    duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Remaining minutes beyond the total hours.",
    )
 
    # ─── Media ────────────────────────────────────────────────────────────────
 
    thumbnail_url = models.URLField(
        blank=True,
        default="",
        help_text="External URL to course thumbnail. No local storage at MVP.",
    )
 
    # ─── Access & Certification ───────────────────────────────────────────────
 
    is_free = models.BooleanField(
        default=True,
        help_text="All MVP content is free. Flag reserved for future paid content.",
    )
    certificate_available = models.BooleanField(
        default=False,
        help_text="Whether the source platform offers a completion certificate.",
    )
 
    # ─── Ratings (from source) ────────────────────────────────────────────────
    # Ratings are pulled from the source platform.
    # Users do NOT rate individual courses on this platform (master ref §3).
 
    rating_average = models.FloatField(
        default=0.0,
        help_text="Average rating pulled from the source platform.",
    )
    rating_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of ratings on the source platform.",
    )
 
    # ─── Source Metadata ──────────────────────────────────────────────────────
    # Stores the original data from the ingestion source.
    # Required for attribution compliance and enabling reprocessing.
    # See master reference §2: "Store source_metadata on every course."
 
    source_metadata = models.JSONField(
        default=dict,
        help_text=(
            "Original data from the ingestion source. "
            "Keys: original_title, original_description, api_source, external_id. "
            "Never modified after ingestion. Enables reprocessing."
        ),
    )
 
    # ─── Full-Text Search Vector ──────────────────────────────────────────────
    # Populated by a signal or migration. Enables PostgreSQL native FTS.
    # See master reference §3: "Basic keyword search using tsvector."
 
    search_vector = SearchVectorField(
        null=True,
        blank=True,
        help_text="PostgreSQL tsvector for full-text search. Auto-updated on save.",
    )
 
    # ─── Visibility ───────────────────────────────────────────────────────────
 
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Inactive courses are hidden from public listings but retained in the DB. "
            "Set to False when a course is no longer available on its source platform. "
            "DO NOT use this field for language filtering — use language_status instead."
        ),
    )
 
    # ─── Language Quality Gate ────────────────────────────────────────────────
    # Set by the multi-layer language detection pipeline in:
    #   apps/ingestion/normalizer.py → LanguageDetector
    #   apps/courses/management/commands/flag_language_status.py (retroactive scan)
    #
    # Do not conflate with is_active. They are independent states:
    #   is_active=False      → course gone from source platform
    #   language_status=rejected → course is non-English
    # A course can be active but rejected, or inactive but accepted.
 
    language_status = models.CharField(
        max_length=10,
        choices=LanguageStatus.choices,
        default=LanguageStatus.UNKNOWN,
        help_text=(
            "Result of the multi-layer language quality pipeline. "
            "unknown: not yet checked. "
            "accepted: confirmed English. "
            "flagged: uncertain, held for human review (still visible). "
            "rejected: confident non-English, hidden from catalog."
        ),
    )
    language_rejection_reason = models.CharField(
        max_length=300,
        blank=True,
        default="",
        help_text=(
            "Why this course was flagged or rejected by the language pipeline. "
            "Examples: 'arabic_script_detected (confidence: 0.95)' or "
            "'lingua_detected_spanish (confidence: 0.92)'. "
            "Empty for accepted and unknown courses."
        ),
    )
 
    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        db_table = "courses"
        indexes = [
            models.Index(fields=["provider"], name="idx_course_provider"),
            models.Index(fields=["category"], name="idx_course_category"),
            models.Index(fields=["level"], name="idx_course_level"),
            models.Index(fields=["age_group"], name="idx_course_age_group"),
            models.Index(fields=["is_active"], name="idx_course_active"),
            models.Index(fields=["language_status"], name="idx_course_language_status"),
            GinIndex(fields=["search_vector"], name="idx_course_search_vector"),
        ]
 
    def __str__(self):
        return f"{self.title} ({self.provider})"
 