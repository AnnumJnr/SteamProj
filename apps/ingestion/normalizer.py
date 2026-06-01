"""
Ingestion normalizer.

Converts RawCourse objects (output of source fetchers) into validated
NormalizedCourse dicts that match the Course model's field schema exactly.

This is the transformation layer between raw external data and the database.

Responsibilities:
- Validate and coerce field types
- Map raw level/age/category strings to Course model choices
- Apply keyword heuristics for missing category/level/age_group fields
- Build the source_metadata dict (preserved verbatim after this point)
- Return a NormalizedCourse or None if the raw data is unrecoverable

Rules enforced:
- Rule 1: All normalization logic lives here — not in sources, not in pipeline
- Rule 5: Validation of field values happens here (format/type layer)
- Rule 9: normalizer is pure — no DB access, no side effects
- Rule 13: Explicit mapping tables — no regex magic for category detection
- Rule 14: One job — transform RawCourse → NormalizedCourse
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from apps.courses.models import Course
from apps.ingestion.sources.base import RawCourse

logger = logging.getLogger(__name__)


# ─── Output Container ─────────────────────────────────────────────────────────

@dataclass
class NormalizedCourse:
    """
    Validated course data ready to be written to the database.

    All fields map directly to Course model fields.
    This is what the pipeline passes to CourseIngestionService.upsert_course().

    Rule 10: This structure must match the Course model schema exactly.
    """
    # Required
    title: str
    source_url: str
    provider: str
    provider_type: str
    category: str
    external_id: str

    # Descriptive
    short_description: str = ""
    full_description: str = ""
    instructor: str = ""
    thumbnail_url: str = ""
    language: str = "en"

    # Classification
    sub_category: str = ""
    level: str = Course.Level.BEGINNER
    age_group: str = Course.AgeGroup.ADULTS
    format: str = Course.Format.VIDEO

    # Duration
    duration_hours: int = 0
    duration_minutes: int = 0

    # Ratings
    rating_average: float = 0.0
    rating_count: int = 0

    # Structured content
    tags: list = field(default_factory=list)
    learning_outcomes: list = field(default_factory=list)
    prerequisites: list = field(default_factory=list)

    # Flags
    is_free: bool = True
    certificate_available: bool = False

    # Preserved original data — written once, never modified
    source_metadata: dict = field(default_factory=dict)


# ─── Mapping Tables ───────────────────────────────────────────────────────────
# Rule 13: Explicit mapping tables — no dynamic logic or regex for these.

# Maps raw provider strings → Course.Provider choices (exact match required)
PROVIDER_MAP: dict[str, str] = {
    "YouTube": Course.Provider.YOUTUBE,
    "freeCodeCamp": Course.Provider.FREECODECAMP,
    "MIT OCW": Course.Provider.MIT_OCW,
    "OpenStax": Course.Provider.OPENSTAX,
    "CK-12": Course.Provider.CK12,
    "Khan Academy": Course.Provider.KHAN_ACADEMY,
}

# Maps provider → provider_type
PROVIDER_TYPE_MAP: dict[str, str] = {
    Course.Provider.YOUTUBE: Course.ProviderType.VIDEO_PLATFORM,
    Course.Provider.FREECODECAMP: Course.ProviderType.LEARNING_PLATFORM,
    Course.Provider.MIT_OCW: Course.ProviderType.UNIVERSITY,
    Course.Provider.OPENSTAX: Course.ProviderType.OPEN_TEXTBOOK,
    Course.Provider.CK12: Course.ProviderType.LEARNING_PLATFORM,
    Course.Provider.KHAN_ACADEMY: Course.ProviderType.LEARNING_PLATFORM,
}

# Maps raw level strings → Course.Level choices
LEVEL_MAP: dict[str, str] = {
    # Explicit values
    "beginner": Course.Level.BEGINNER,
    "intermediate": Course.Level.INTERMEDIATE,
    "advanced": Course.Level.ADVANCED,
    # MIT OCW values
    "undergraduate": Course.Level.INTERMEDIATE,
    "graduate": Course.Level.ADVANCED,
    "high school": Course.Level.BEGINNER,
    # Common variations
    "introductory": Course.Level.BEGINNER,
    "intro": Course.Level.BEGINNER,
    "elementary": Course.Level.BEGINNER,
    "upper": Course.Level.ADVANCED,
    "upper-division": Course.Level.ADVANCED,
}

# Maps raw age group strings → Course.AgeGroup choices
AGE_GROUP_MAP: dict[str, str] = {
    "kids": Course.AgeGroup.KIDS,
    "children": Course.AgeGroup.KIDS,
    "k-5": Course.AgeGroup.KIDS,
    "elementary": Course.AgeGroup.KIDS,
    "teens": Course.AgeGroup.TEENS,
    "teen": Course.AgeGroup.TEENS,
    "middle school": Course.AgeGroup.TEENS,
    "high school": Course.AgeGroup.TEENS,
    "secondary": Course.AgeGroup.TEENS,
    "adults": Course.AgeGroup.ADULTS,
    "adult": Course.AgeGroup.ADULTS,
    "college": Course.AgeGroup.ADULTS,
    "university": Course.AgeGroup.ADULTS,
    "undergraduate": Course.AgeGroup.ADULTS,
    "graduate": Course.AgeGroup.ADULTS,
    "professional": Course.AgeGroup.ADULTS,
}

# Valid category values (from Course.Category)
VALID_CATEGORIES: set[str] = {
    Course.Category.COMPUTER_SCIENCE,
    Course.Category.MATHEMATICS,
    Course.Category.NATURAL_SCIENCES,
    Course.Category.ENGINEERING,
    Course.Category.TECHNOLOGY_APPLIED,
    Course.Category.STEM_FOUNDATIONS,
}

# Valid format values
VALID_FORMATS: set[str] = {
    Course.Format.VIDEO,
    Course.Format.TEXT,
    Course.Format.INTERACTIVE,
}

# ─── Keyword Heuristics ───────────────────────────────────────────────────────
# Used ONLY when a field is blank — sources should pre-populate when possible.
# Keywords are lowercase. Checked against title + description combined.
# Rule 13: Ordered lists — first match wins. More specific terms listed first.

CATEGORY_KEYWORDS: list[tuple[str, str]] = [
    # Computer Science
    ("machine learning", Course.Category.COMPUTER_SCIENCE),
    ("artificial intelligence", Course.Category.COMPUTER_SCIENCE),
    ("deep learning", Course.Category.COMPUTER_SCIENCE),
    ("data science", Course.Category.COMPUTER_SCIENCE),
    ("programming", Course.Category.COMPUTER_SCIENCE),
    ("python", Course.Category.COMPUTER_SCIENCE),
    ("javascript", Course.Category.COMPUTER_SCIENCE),
    ("computer science", Course.Category.COMPUTER_SCIENCE),
    ("algorithms", Course.Category.COMPUTER_SCIENCE),
    ("data structures", Course.Category.COMPUTER_SCIENCE),
    ("web development", Course.Category.TECHNOLOGY_APPLIED),
    ("software", Course.Category.COMPUTER_SCIENCE),
    ("coding", Course.Category.COMPUTER_SCIENCE),
    # Mathematics
    ("calculus", Course.Category.MATHEMATICS),
    ("algebra", Course.Category.MATHEMATICS),
    ("geometry", Course.Category.MATHEMATICS),
    ("statistics", Course.Category.MATHEMATICS),
    ("mathematics", Course.Category.MATHEMATICS),
    ("probability", Course.Category.MATHEMATICS),
    ("linear algebra", Course.Category.MATHEMATICS),
    ("trigonometry", Course.Category.MATHEMATICS),
    # Natural Sciences
    ("physics", Course.Category.NATURAL_SCIENCES),
    ("chemistry", Course.Category.NATURAL_SCIENCES),
    ("biology", Course.Category.NATURAL_SCIENCES),
    ("earth science", Course.Category.NATURAL_SCIENCES),
    ("astronomy", Course.Category.NATURAL_SCIENCES),
    ("neuroscience", Course.Category.NATURAL_SCIENCES),
    ("ecology", Course.Category.NATURAL_SCIENCES),
    ("genetics", Course.Category.NATURAL_SCIENCES),
    # Engineering
    ("mechanical engineering", Course.Category.ENGINEERING),
    ("electrical engineering", Course.Category.ENGINEERING),
    ("civil engineering", Course.Category.ENGINEERING),
    ("chemical engineering", Course.Category.ENGINEERING),
    ("engineering", Course.Category.ENGINEERING),
    ("robotics", Course.Category.ENGINEERING),
    ("circuits", Course.Category.ENGINEERING),
    # Technology & Applied Skills
    ("technology", Course.Category.TECHNOLOGY_APPLIED),
    ("design", Course.Category.TECHNOLOGY_APPLIED),
    ("3d printing", Course.Category.TECHNOLOGY_APPLIED),
    ("cybersecurity", Course.Category.TECHNOLOGY_APPLIED),
    ("networking", Course.Category.TECHNOLOGY_APPLIED),
]

LEVEL_KEYWORDS: list[tuple[str, str]] = [
    ("advanced", Course.Level.ADVANCED),
    ("graduate", Course.Level.ADVANCED),
    ("expert", Course.Level.ADVANCED),
    ("intermediate", Course.Level.INTERMEDIATE),
    ("undergraduate", Course.Level.INTERMEDIATE),
    ("college", Course.Level.INTERMEDIATE),
    ("beginner", Course.Level.BEGINNER),
    ("introduction", Course.Level.BEGINNER),
    ("intro to", Course.Level.BEGINNER),
    ("fundamentals", Course.Level.BEGINNER),
    ("basics", Course.Level.BEGINNER),
    ("for kids", Course.Level.BEGINNER),
    ("elementary", Course.Level.BEGINNER),
]


# ─── Normalizer ───────────────────────────────────────────────────────────────

class CourseNormalizer:
    """
    Transforms a RawCourse into a NormalizedCourse.

    All public logic goes through normalize(). Private methods handle
    individual field transformations.

    Rule 9: No side effects — no DB reads/writes, no events, no logging
            of individual field decisions (only warnings for failures).
    Rule 14: One job — transform. Pipeline and service handle everything else.
    """

    def normalize(self, raw: RawCourse) -> NormalizedCourse | None:
        """
        Convert a RawCourse into a NormalizedCourse.

        Returns None if the raw data is unrecoverable (missing required fields).
        Logs a warning for any course that cannot be normalized.

        Rule 1: All normalization logic is in this class.
        Rule 5: Field validation happens here.
        """
        # ── Validate required fields ──
        if not raw.external_id or not raw.title or not raw.source_url:
            logger.warning(
                "CourseNormalizer.normalize: Skipping course missing required fields. "
                "external_id=%s title=%s source_url=%s",
                raw.external_id,
                raw.title,
                raw.source_url,
            )
            return None

        # ── Resolve provider ──
        provider = self._normalize_provider(raw.provider)
        if not provider:
            logger.warning(
                "CourseNormalizer.normalize: Unknown provider '%s' for course '%s'. Skipping.",
                raw.provider,
                raw.title,
            )
            return None

        provider_type = PROVIDER_TYPE_MAP.get(provider, Course.ProviderType.LEARNING_PLATFORM)

        # ── Build search text for heuristics (title + description) ──
        search_text = f"{raw.title} {raw.short_description} {raw.full_description}".lower()

        # ── Resolve classification fields ──
        category = self._normalize_category(raw.category, search_text)
        level = self._normalize_level(raw.level, search_text)
        age_group = self._normalize_age_group(raw.age_group, level)
        format_ = self._normalize_format(raw.format)

        # ── Sanitize text fields ──
        title = raw.title.strip()[:500]
        short_description = (raw.short_description or "").strip()[:300]
        full_description = (raw.full_description or "").strip()
        instructor = (raw.instructor or "").strip()[:200]
        language = (raw.language or "en").strip()[:10]
        thumbnail_url = (raw.thumbnail_url or "").strip()
        sub_category = (raw.sub_category or "").strip()[:100]

        # ── Sanitize numeric fields ──
        duration_hours = max(0, int(raw.duration_hours or 0))
        duration_minutes = max(0, int(raw.duration_minutes or 0))
        rating_average = max(0.0, float(raw.rating_average or 0.0))
        rating_count = max(0, int(raw.rating_count or 0))

        # ── Sanitize list fields ──
        tags = self._sanitize_string_list(raw.tags)
        learning_outcomes = self._sanitize_string_list(raw.learning_outcomes)
        prerequisites = self._sanitize_string_list(raw.prerequisites)

        # ── Build source_metadata (preserved verbatim) ──
        source_metadata = {
            "original_title": raw.title,
            "original_description": raw.full_description or raw.short_description,
            "api_source": provider,
            "external_id": raw.external_id,
            "raw_payload": raw.raw_payload,
        }

        return NormalizedCourse(
            title=title,
            short_description=short_description,
            full_description=full_description,
            source_url=raw.source_url,
            provider=provider,
            provider_type=provider_type,
            instructor=instructor,
            thumbnail_url=thumbnail_url,
            language=language,
            category=category,
            sub_category=sub_category,
            level=level,
            age_group=age_group,
            format=format_,
            duration_hours=duration_hours,
            duration_minutes=duration_minutes,
            rating_average=rating_average,
            rating_count=rating_count,
            tags=tags,
            learning_outcomes=learning_outcomes,
            prerequisites=prerequisites,
            is_free=bool(raw.is_free),
            certificate_available=bool(raw.certificate_available),
            external_id=raw.external_id,
            source_metadata=source_metadata,
        )

    # ─── Private: Field Normalizers ───────────────────────────────────────────

    def _normalize_provider(self, raw_provider: str) -> str | None:
        """Map raw provider string to Course.Provider choice. Returns None if unknown."""
        return PROVIDER_MAP.get(raw_provider)

    def _normalize_category(self, raw_category: str, search_text: str) -> str:
        """
        Resolve the STEM category.

        Priority:
        1. Use raw_category if it already matches a valid Course.Category value
        2. Apply keyword heuristics against title + description
        3. Default to STEM_FOUNDATIONS

        Rule 13: Explicit mapping — keyword list is ordered, first match wins.
        """
        # Priority 1: direct match
        if raw_category in VALID_CATEGORIES:
            return raw_category

        # Priority 2: keyword heuristics
        for keyword, category in CATEGORY_KEYWORDS:
            if keyword in search_text:
                return category

        # Priority 3: default
        logger.warning(
            "CourseNormalizer._normalize_category: Could not determine category "
            "from raw='%s'. Defaulting to STEM_FOUNDATIONS.",
            raw_category,
        )
        return Course.Category.STEM_FOUNDATIONS

    def _normalize_level(self, raw_level: str, search_text: str) -> str:
        """
        Resolve the course difficulty level.

        Priority:
        1. Direct match against LEVEL_MAP (case-insensitive)
        2. Keyword heuristics against title + description
        3. Default to Beginner

        Rule 13: Explicit mapping table + ordered keyword list.
        """
        if raw_level:
            normalized = LEVEL_MAP.get(raw_level.lower().strip())
            if normalized:
                return normalized

        # Keyword heuristics
        for keyword, level in LEVEL_KEYWORDS:
            if keyword in search_text:
                return level

        return Course.Level.BEGINNER

    def _normalize_age_group(self, raw_age_group: str, level: str) -> str:
        """
        Resolve the target age group.

        Priority:
        1. Direct match against AGE_GROUP_MAP (case-insensitive)
        2. Infer from level (Graduate/Advanced → Adults, Beginner → Kids if no signal)
        3. Default to Adults

        Rule 13: Explicit mapping — inference is a fallback, not primary logic.
        """
        if raw_age_group:
            normalized = AGE_GROUP_MAP.get(raw_age_group.lower().strip())
            if normalized:
                return normalized

        # Infer from level as a secondary signal
        if level == Course.Level.ADVANCED:
            return Course.AgeGroup.ADULTS

        return Course.AgeGroup.ADULTS

    def _normalize_format(self, raw_format: str) -> str:
        """
        Validate the content format.

        If the raw value matches a valid Course.Format choice, use it.
        Otherwise default to Video (most common format for MVP sources).
        """
        if raw_format in VALID_FORMATS:
            return raw_format
        return Course.Format.VIDEO

    def _sanitize_string_list(self, raw_list: Any) -> list[str]:
        """
        Ensure a field is a clean list of non-empty strings.

        Handles: None, non-list types, lists with non-string items.
        Rule 13: Explicit — no comprehension magic.
        """
        if not raw_list:
            return []
        if not isinstance(raw_list, list):
            return []

        result = []
        for item in raw_list:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
        return result