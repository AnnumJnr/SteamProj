"""
Ingestion normalizer.

Converts RawCourse objects (output of source fetchers) into validated
NormalizedCourse dicts that match the Course model's field schema exactly.

This is the transformation layer between raw external data and the database.

Responsibilities:
- Validate and coerce field types
- Map raw level/age/category strings to Course model choices
- Apply keyword heuristics for missing category/level/age_group fields
- Run the multi-layer language quality pipeline on every course
- Build the source_metadata dict (preserved verbatim after this point)
- Return a NormalizedCourse or None if the raw data is unrecoverable

Changes from v1 (language pipeline improvements):
- Layer 1 now reads audio_language from raw_payload['audio_language'] when
  available (YouTube only). This is the actual spoken language of the content,
  far more reliable than the generic language field which defaulted to 'en'.
- Added Layer 0: thin content detection. When a course has a short/generic
  title AND no description, there is no meaningful text to evaluate. These
  courses are flagged automatically for human review rather than silently
  accepted. This directly addresses the 'AD ASF MATHS LECS' class of problem
  where the pipeline had nothing to detect on and passed the course by default.
- Thin content threshold: title <= 30 chars AND description < 20 chars.
  Confidence contribution: 0.55 (pushes course into FLAGGED territory alone).
 
Rules enforced:
- Rule 1: All normalization logic lives here — not in sources, not in pipeline
- Rule 5: Validation of field values happens here (format/type layer)
- Rule 9: normalizer is pure — no DB access, no side effects
- Rule 13: Explicit mapping tables — no regex magic for category detection
- Rule 14: One job — transform RawCourse → NormalizedCourse
"""
 
import logging
import unicodedata
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
 
    # Language quality pipeline output — set by LanguageDetector
    language_status: str = Course.LanguageStatus.UNKNOWN
    language_rejection_reason: str = ""
 
    # Preserved original data — written once, never modified
    source_metadata: dict = field(default_factory=dict)
 
 
# ─── Mapping Tables ───────────────────────────────────────────────────────────
 
PROVIDER_MAP: dict[str, str] = {
    "YouTube": Course.Provider.YOUTUBE,
    "freeCodeCamp": Course.Provider.FREECODECAMP,
    "MIT OCW": Course.Provider.MIT_OCW,
    "OpenStax": Course.Provider.OPENSTAX,
    "CK-12": Course.Provider.CK12,
    "Khan Academy": Course.Provider.KHAN_ACADEMY,
}
 
PROVIDER_TYPE_MAP: dict[str, str] = {
    Course.Provider.YOUTUBE: Course.ProviderType.VIDEO_PLATFORM,
    Course.Provider.FREECODECAMP: Course.ProviderType.LEARNING_PLATFORM,
    Course.Provider.MIT_OCW: Course.ProviderType.UNIVERSITY,
    Course.Provider.OPENSTAX: Course.ProviderType.OPEN_TEXTBOOK,
    Course.Provider.CK12: Course.ProviderType.LEARNING_PLATFORM,
    Course.Provider.KHAN_ACADEMY: Course.ProviderType.LEARNING_PLATFORM,
}
 
LEVEL_MAP: dict[str, str] = {
    "beginner": Course.Level.BEGINNER,
    "intermediate": Course.Level.INTERMEDIATE,
    "advanced": Course.Level.ADVANCED,
    "undergraduate": Course.Level.INTERMEDIATE,
    "graduate": Course.Level.ADVANCED,
    "high school": Course.Level.BEGINNER,
    "introductory": Course.Level.BEGINNER,
    "intro": Course.Level.BEGINNER,
    "elementary": Course.Level.BEGINNER,
    "upper": Course.Level.ADVANCED,
    "upper-division": Course.Level.ADVANCED,
}
 
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
 
VALID_CATEGORIES: set[str] = {
    Course.Category.COMPUTER_SCIENCE,
    Course.Category.MATHEMATICS,
    Course.Category.NATURAL_SCIENCES,
    Course.Category.ENGINEERING,
    Course.Category.TECHNOLOGY_APPLIED,
    Course.Category.STEM_FOUNDATIONS,
}
 
VALID_FORMATS: set[str] = {
    Course.Format.VIDEO,
    Course.Format.TEXT,
    Course.Format.INTERACTIVE,
}
 
CATEGORY_KEYWORDS: list[tuple[str, str]] = [
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
    ("software", Course.Category.COMPUTER_SCIENCE),
    ("coding", Course.Category.COMPUTER_SCIENCE),
    ("web development", Course.Category.TECHNOLOGY_APPLIED),
    ("calculus", Course.Category.MATHEMATICS),
    ("algebra", Course.Category.MATHEMATICS),
    ("geometry", Course.Category.MATHEMATICS),
    ("statistics", Course.Category.MATHEMATICS),
    ("mathematics", Course.Category.MATHEMATICS),
    ("probability", Course.Category.MATHEMATICS),
    ("linear algebra", Course.Category.MATHEMATICS),
    ("trigonometry", Course.Category.MATHEMATICS),
    ("physics", Course.Category.NATURAL_SCIENCES),
    ("chemistry", Course.Category.NATURAL_SCIENCES),
    ("biology", Course.Category.NATURAL_SCIENCES),
    ("earth science", Course.Category.NATURAL_SCIENCES),
    ("astronomy", Course.Category.NATURAL_SCIENCES),
    ("neuroscience", Course.Category.NATURAL_SCIENCES),
    ("ecology", Course.Category.NATURAL_SCIENCES),
    ("genetics", Course.Category.NATURAL_SCIENCES),
    ("mechanical engineering", Course.Category.ENGINEERING),
    ("electrical engineering", Course.Category.ENGINEERING),
    ("civil engineering", Course.Category.ENGINEERING),
    ("chemical engineering", Course.Category.ENGINEERING),
    ("engineering", Course.Category.ENGINEERING),
    ("robotics", Course.Category.ENGINEERING),
    ("circuits", Course.Category.ENGINEERING),
    ("technology", Course.Category.TECHNOLOGY_APPLIED),
    ("applied", Course.Category.TECHNOLOGY_APPLIED),
    ("science", Course.Category.STEM_FOUNDATIONS),
    ("stem", Course.Category.STEM_FOUNDATIONS),
]
 
LEVEL_KEYWORDS: list[tuple[str, str]] = [
    ("advanced", Course.Level.ADVANCED),
    ("expert", Course.Level.ADVANCED),
    ("graduate", Course.Level.ADVANCED),
    ("intermediate", Course.Level.INTERMEDIATE),
    ("beginner", Course.Level.BEGINNER),
    ("introduction", Course.Level.BEGINNER),
    ("intro to", Course.Level.BEGINNER),
    ("fundamentals", Course.Level.BEGINNER),
    ("basics", Course.Level.BEGINNER),
    ("for beginners", Course.Level.BEGINNER),
]
 
# ─── Language Detection Constants ─────────────────────────────────────────────
 
# Confidence contributions per layer
LAYER_THIN_CONTENT      = 0.55   # Layer 0: no description + short/ambiguous title
LAYER_METADATA_NON_ENGLISH = 0.30  # Layer 1: language/audio field says non-English
LAYER_UNICODE_SCRIPT    = 0.90   # Layer 2: non-Latin characters detected
LAYER_LINGUA_DETECTION  = 0.70   # Layer 3: Lingua detects non-English language
 
REJECT_THRESHOLD = 0.85   # >= this → REJECTED (hidden from catalog)
FLAG_THRESHOLD   = 0.50   # >= this → FLAGGED (visible, needs human review)
 
# Thin content thresholds (Layer 0)
# A title at or below this length with no description has too little text
# to make any reliable language determination.
THIN_TITLE_MAX_CHARS = 30
THIN_DESCRIPTION_MIN_CHARS = 20
 
# Minimum ratio of non-Latin characters to trigger Layer 2
NON_LATIN_RATIO_THRESHOLD = 0.15
 
# Non-Latin Unicode blocks
NON_LATIN_BLOCKS: list[tuple[int, int, str]] = [
    (0x0600, 0x06FF, "arabic"),
    (0x0750, 0x077F, "arabic_supplement"),
    (0x08A0, 0x08FF, "arabic_extended"),
    (0x0900, 0x097F, "devanagari"),
    (0x0980, 0x09FF, "bengali"),
    (0x0A00, 0x0A7F, "gurmukhi"),
    (0x0A80, 0x0AFF, "gujarati"),
    (0x0B00, 0x0B7F, "oriya"),
    (0x0B80, 0x0BFF, "tamil"),
    (0x0C00, 0x0C7F, "telugu"),
    (0x0C80, 0x0CFF, "kannada"),
    (0x0D00, 0x0D7F, "malayalam"),
    (0x0E00, 0x0E7F, "thai"),
    (0x0E80, 0x0EFF, "lao"),
    (0x0F00, 0x0FFF, "tibetan"),
    (0x1000, 0x109F, "myanmar"),
    (0x1100, 0x11FF, "hangul_jamo"),
    (0x3040, 0x30FF, "japanese"),
    (0x3400, 0x4DBF, "cjk_extension"),
    (0x4E00, 0x9FFF, "cjk_unified"),
    (0xAC00, 0xD7AF, "hangul"),
    (0x0400, 0x04FF, "cyrillic"),
    (0x0370, 0x03FF, "greek"),
]
 
NON_ENGLISH_LANGUAGE_CODES: set[str] = {
    "ar", "hi", "ur", "fa", "bn", "pa", "gu", "mr", "ta", "te", "kn", "ml",
    "zh", "ja", "ko", "th", "vi", "ru", "de", "fr", "es", "pt", "it", "nl",
    "pl", "tr", "id", "ms", "sw", "ha", "yo", "ig", "am", "so", "tl",
}
 
 
# ─── Language Detector ────────────────────────────────────────────────────────
 
class LanguageDetector:
    """
    Multi-layer language confidence pipeline.
 
    Layer 0: Thin content detection (NEW)
      When a course has a very short title AND no meaningful description,
      there is not enough text to make any reliable language determination.
      These are flagged for human review automatically.
      Confidence contribution: 0.55 (FLAG threshold is 0.50).
 
    Layer 1: Metadata language field / audio language
      For YouTube: reads defaultAudioLanguage from raw_payload — the actual
      spoken language tagged by the channel owner in YouTube Studio. This is
      the most reliable metadata signal available without inspecting the video.
      For all sources: reads the language field from the normalizer.
      Confidence contribution: 0.30 (low trust — often missing or wrong).
 
    Layer 2: Unicode script detection
      Counts characters in non-Latin Unicode blocks. High confidence signal —
      non-Latin script in a title is almost never accidental.
      Confidence contribution: 0.90.
 
    Layer 3: Lingua language detection
      Detects the language of Latin-script text. Catches Spanish, French,
      Indonesian, Urdu-in-Latin-script, etc. that Layer 2 cannot detect.
      Confidence contribution: 0.70 when confident (>= 0.70 Lingua score).
 
    Final thresholds:
      confidence >= 0.85 → REJECTED  (hidden from catalog)
      confidence >= 0.50 → FLAGGED   (visible, held for human review)
      confidence <  0.50 → ACCEPTED  (English confirmed)
 
    Rule 9: Pure — no DB access, no side effects.
    Rule 14: One job — detect language and return status + reason.
    """
 
    def __init__(self):
        self._lingua_detector = None
        self._lingua_available = None
 
    def _get_lingua_detector(self):
        """Initialise the Lingua detector on first call. Returns None if not installed."""
        if self._lingua_available is False:
            return None
        if self._lingua_detector is not None:
            return self._lingua_detector
 
        try:
            from lingua import Language, LanguageDetectorBuilder
 
            languages = [
                Language.ENGLISH,
                Language.ARABIC,
                Language.HINDI,
                Language.URDU,
                Language.SPANISH,
                Language.FRENCH,
                Language.PORTUGUESE,
                Language.INDONESIAN,
                Language.GERMAN,
                Language.TURKISH,
                Language.RUSSIAN,
                Language.CHINESE,
                Language.JAPANESE,
                Language.KOREAN,
                Language.BENGALI,
                Language.PERSIAN,
            ]
 
            self._lingua_detector = (
                LanguageDetectorBuilder
                .from_languages(*languages)
                .with_minimum_relative_distance(0.1)
                .build()
            )
            self._lingua_available = True
            logger.debug("LanguageDetector: Lingua detector initialised successfully.")
 
        except ImportError:
            self._lingua_available = False
            logger.warning(
                "LanguageDetector: lingua-language-detector not installed. "
                "Layer 3 (Lingua) will be skipped. "
                "Install with: pip install lingua-language-detector"
            )
 
        return self._lingua_detector
 
    def detect(
        self,
        title: str,
        description: str,
        metadata_language: str,
        audio_language: str = "",
    ) -> dict:
        """
        Run the four-layer pipeline on a course's text content.
 
        Args:
            title: Course title
            description: Short or full description (whichever is available)
            metadata_language: ISO 639-1 code from source metadata (e.g. 'en', 'ar')
            audio_language: defaultAudioLanguage from YouTube API (YouTube only).
                            Takes precedence over metadata_language in Layer 1.
 
        Returns:
        {
            "language_status": "accepted" | "flagged" | "rejected",
            "language_rejection_reason": str,
            "confidence": float,
            "layers_triggered": list[str],
        }
        """
        confidence = 0.0
        layers_triggered = []
        reason_parts = []
 
        text = f"{title} {description}".strip()
 
        # ── Layer 0: Thin content detection ───────────────────────────────────
        # When there is not enough text to make a language determination,
        # flag the course for human review rather than silently accepting it.
        #
        # Conditions that trigger this layer (both must be true):
        #   1. Title is short or generic (<= 30 characters)
        #   2. Description is absent or negligible (< 20 characters)
        #
        # Why 0.55 contribution: this alone pushes the course above the FLAG
        # threshold (0.50) but NOT above the REJECT threshold (0.85). A human
        # must make the final call — the pipeline cannot confirm or deny English
        # on insufficient evidence.
        #
        # Examples that trigger: "AD ASF MATHS LECS" (no description)
        # Examples that do NOT trigger: "Python for Beginners Full Course" (clear title)
        title_stripped = title.strip()
        desc_stripped = description.strip()
        is_thin_title = len(title_stripped) <= THIN_TITLE_MAX_CHARS
        is_empty_desc = len(desc_stripped) < THIN_DESCRIPTION_MIN_CHARS
 
        if is_thin_title and is_empty_desc:
            confidence += LAYER_THIN_CONTENT
            layers_triggered.append("thin_content")
            reason_parts.append(
                f"thin_content (title_len={len(title_stripped)}, "
                f"desc_len={len(desc_stripped)})"
            )
            logger.debug(
                "LanguageDetector: Layer 0 (thin_content) triggered. "
                "title='%s' title_len=%d desc_len=%d contribution=%.2f",
                title_stripped,
                len(title_stripped),
                len(desc_stripped),
                LAYER_THIN_CONTENT,
            )
 
        # ── Layer 1: Metadata / audio language field ──────────────────────────
        # Priority: audio_language (YouTube's defaultAudioLanguage) over
        # metadata_language (the generic language field).
        #
        # audio_language reflects the actual spoken language of the content
        # and is set by channel owners in YouTube Studio. It is the most
        # reliable metadata signal available without inspecting the video.
        #
        # metadata_language is used for all non-YouTube sources and as a
        # fallback. Low trust because the normalizer previously defaulted
        # everything to 'en' when no language was provided by the source.
        effective_language = (audio_language or metadata_language or "").strip().lower()[:2]
 
        if effective_language and effective_language != "en":
            if effective_language in NON_ENGLISH_LANGUAGE_CODES:
                confidence += LAYER_METADATA_NON_ENGLISH
                layers_triggered.append("metadata_language")
                signal_source = "audio_language" if audio_language else "metadata_language"
                reason_parts.append(
                    f"{signal_source}={effective_language}"
                    f" (confidence: {LAYER_METADATA_NON_ENGLISH:.2f})"
                )
                logger.debug(
                    "LanguageDetector: Layer 1 triggered. "
                    "source=%s lang=%s contribution=%.2f",
                    signal_source,
                    effective_language,
                    LAYER_METADATA_NON_ENGLISH,
                )
 
        # ── Layer 2: Unicode script detection ────────────────────────────────
        script_result = self._detect_non_latin_script(text)
        if script_result["triggered"]:
            confidence += LAYER_UNICODE_SCRIPT
            layers_triggered.append("unicode_script")
            reason_parts.append(
                f"{script_result['dominant_script']}_script_detected"
                f" (ratio: {script_result['ratio']:.2f})"
            )
            logger.debug(
                "LanguageDetector: Layer 2 triggered. script=%s ratio=%.2f contribution=%.2f",
                script_result["dominant_script"],
                script_result["ratio"],
                LAYER_UNICODE_SCRIPT,
            )
 
        # ── Layer 3: Lingua language detection ───────────────────────────────
        # Only runs if there is enough text for Lingua to be reliable.
        # Lingua needs meaningful words — very short text gives unreliable results.
        # The threshold here is longer than in v1 (25 chars vs 10) because
        # short Latin-script text is the most error-prone input for Lingua.
        if len(text) >= 25:
            lingua_result = self._detect_with_lingua(text)
            if lingua_result["triggered"]:
                confidence += LAYER_LINGUA_DETECTION
                layers_triggered.append("lingua")
                reason_parts.append(
                    f"lingua_detected_{lingua_result['language']}"
                    f" (confidence: {lingua_result['confidence']:.2f})"
                )
                logger.debug(
                    "LanguageDetector: Layer 3 triggered. "
                    "detected=%s confidence=%.2f contribution=%.2f",
                    lingua_result["language"],
                    lingua_result["confidence"],
                    LAYER_LINGUA_DETECTION,
                )
 
        # ── Final decision ────────────────────────────────────────────────────
        if confidence >= REJECT_THRESHOLD:
            status = Course.LanguageStatus.REJECTED
            rejection_reason = (
                "; ".join(reason_parts)
                + f" [total_confidence: {confidence:.2f}]"
            )
        elif confidence >= FLAG_THRESHOLD:
            status = Course.LanguageStatus.FLAGGED
            rejection_reason = (
                "; ".join(reason_parts)
                + f" [total_confidence: {confidence:.2f}, flagged_for_review]"
            )
        else:
            status = Course.LanguageStatus.ACCEPTED
            rejection_reason = ""
 
        return {
            "language_status": status,
            "language_rejection_reason": rejection_reason,
            "confidence": confidence,
            "layers_triggered": layers_triggered,
        }
 
    def _detect_non_latin_script(self, text: str) -> dict:
        """Layer 2: Count characters in non-Latin Unicode blocks."""
        if not text:
            return {"triggered": False, "dominant_script": "", "ratio": 0.0}
 
        alpha_chars = [c for c in text if unicodedata.category(c).startswith("L")]
 
        if not alpha_chars:
            return {"triggered": False, "dominant_script": "", "ratio": 0.0}
 
        script_counts: dict[str, int] = {}
        non_latin_total = 0
 
        for char in alpha_chars:
            cp = ord(char)
            for start, end, script_name in NON_LATIN_BLOCKS:
                if start <= cp <= end:
                    script_counts[script_name] = script_counts.get(script_name, 0) + 1
                    non_latin_total += 1
                    break
 
        ratio = non_latin_total / len(alpha_chars)
 
        if ratio < NON_LATIN_RATIO_THRESHOLD:
            return {"triggered": False, "dominant_script": "", "ratio": ratio}
 
        dominant = max(script_counts, key=script_counts.get) if script_counts else "unknown"
        return {"triggered": True, "dominant_script": dominant, "ratio": ratio}
 
    def _detect_with_lingua(self, text: str) -> dict:
        """Layer 3: Use Lingua to detect the language of Latin-script text."""
        detector = self._get_lingua_detector()
        if detector is None:
            return {"triggered": False, "language": "", "confidence": 0.0}
 
        try:
            result = detector.detect_language_of(text)
 
            if result is None:
                return {"triggered": False, "language": "", "confidence": 0.0}
 
            confidence_values = detector.compute_language_confidence_values(text)
            detected_confidence = 0.0
            detected_name = result.name.lower()
 
            for cv in confidence_values:
                if cv.language == result:
                    detected_confidence = cv.value
                    break
 
            if result.name != "ENGLISH" and detected_confidence >= 0.70:
                return {
                    "triggered": True,
                    "language": detected_name,
                    "confidence": detected_confidence,
                }
 
            return {
                "triggered": False,
                "language": detected_name,
                "confidence": detected_confidence,
            }
 
        except Exception as exc:
            logger.warning(
                "LanguageDetector._detect_with_lingua: Lingua raised an exception: %s. "
                "Skipping Layer 3 for this course.",
                exc,
            )
            return {"triggered": False, "language": "", "confidence": 0.0}
 
 
# ─── Normalizer ───────────────────────────────────────────────────────────────
 
class CourseNormalizer:
    """
    Transforms a RawCourse into a NormalizedCourse.
    Pure transformation — no DB access, no external API calls.
    """
 
    def __init__(self):
        self._language_detector = LanguageDetector()
 
    def normalize(self, raw: RawCourse) -> NormalizedCourse | None:
        """
        Convert a RawCourse into a NormalizedCourse.
        Returns None if required fields are missing.
        """
        if not raw.external_id or not raw.title or not raw.source_url:
            logger.warning(
                "CourseNormalizer.normalize: Skipping course missing required fields. "
                "external_id=%s title=%s source_url=%s",
                raw.external_id,
                raw.title,
                raw.source_url,
            )
            return None
 
        provider = self._normalize_provider(raw.provider)
        if not provider:
            logger.warning(
                "CourseNormalizer.normalize: Unknown provider '%s' for '%s'. Skipping.",
                raw.provider,
                raw.title,
            )
            return None
 
        provider_type = PROVIDER_TYPE_MAP.get(provider, Course.ProviderType.LEARNING_PLATFORM)
        search_text = f"{raw.title} {raw.short_description} {raw.full_description}".lower()
 
        category = self._normalize_category(raw.category, search_text)
        level = self._normalize_level(raw.level, search_text)
        age_group = self._normalize_age_group(raw.age_group, level)
        format_ = self._normalize_format(raw.format)
 
        title = raw.title.strip()[:500]
        short_description = (raw.short_description or "").strip()[:300]
        full_description = (raw.full_description or "").strip()
        instructor = (raw.instructor or "").strip()[:200]
        language = (raw.language or "").strip()[:10]
        thumbnail_url = (raw.thumbnail_url or "").strip()
        sub_category = (raw.sub_category or "").strip()[:100]
 
        duration_hours = max(0, int(raw.duration_hours or 0))
        duration_minutes = max(0, int(raw.duration_minutes or 0))
        rating_average = max(0.0, float(raw.rating_average or 0.0))
        rating_count = max(0, int(raw.rating_count or 0))
 
        tags = self._sanitize_string_list(raw.tags)
        learning_outcomes = self._sanitize_string_list(raw.learning_outcomes)
        prerequisites = self._sanitize_string_list(raw.prerequisites)
 
        # ── Language quality pipeline ─────────────────────────────────────────
        # Extract audio_language from raw_payload for YouTube courses.
        # This is defaultAudioLanguage from the YouTube API — the spoken
        # language of the content, not just the metadata language.
        raw_payload = getattr(raw, "raw_payload", {}) or {}
        audio_language = raw_payload.get("audio_language", "") or ""
 
        detection_text = short_description or full_description or ""
        lang_result = self._language_detector.detect(
            title=title,
            description=detection_text,
            metadata_language=language,
            audio_language=audio_language,
        )
 
        if lang_result["language_status"] == Course.LanguageStatus.REJECTED:
            logger.warning(
                "CourseNormalizer.normalize: REJECTED by language pipeline. "
                "title='%s' provider='%s' reason='%s'",
                title, provider, lang_result["language_rejection_reason"],
            )
        elif lang_result["language_status"] == Course.LanguageStatus.FLAGGED:
            logger.warning(
                "CourseNormalizer.normalize: FLAGGED by language pipeline. "
                "title='%s' provider='%s' reason='%s'",
                title, provider, lang_result["language_rejection_reason"],
            )
 
        source_metadata = {
            "original_title": raw.title,
            "original_description": raw.full_description or raw.short_description,
            "api_source": provider,
            "external_id": raw.external_id,
            "raw_payload": raw_payload,
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
            language_status=lang_result["language_status"],
            language_rejection_reason=lang_result["language_rejection_reason"],
        )
 
    # ─── Private: Field Normalizers ───────────────────────────────────────────
 
    def _normalize_provider(self, raw_provider: str) -> str | None:
        return PROVIDER_MAP.get(raw_provider)
 
    def _normalize_category(self, raw_category: str, search_text: str) -> str:
        if raw_category in VALID_CATEGORIES:
            return raw_category
        for keyword, category in CATEGORY_KEYWORDS:
            if keyword in search_text:
                return category
        logger.warning(
            "CourseNormalizer._normalize_category: Could not determine category "
            "from raw='%s'. Defaulting to STEM_FOUNDATIONS.", raw_category,
        )
        return Course.Category.STEM_FOUNDATIONS
 
    def _normalize_level(self, raw_level: str, search_text: str) -> str:
        if raw_level:
            normalized = LEVEL_MAP.get(raw_level.lower().strip())
            if normalized:
                return normalized
        for keyword, level in LEVEL_KEYWORDS:
            if keyword in search_text:
                return level
        return Course.Level.BEGINNER
 
    def _normalize_age_group(self, raw_age_group: str, level: str) -> str:
        if raw_age_group:
            normalized = AGE_GROUP_MAP.get(raw_age_group.lower().strip())
            if normalized:
                return normalized
        if level == Course.Level.ADVANCED:
            return Course.AgeGroup.ADULTS
        return Course.AgeGroup.ADULTS
 
    def _normalize_format(self, raw_format: str) -> str:
        if raw_format in VALID_FORMATS:
            return raw_format
        return Course.Format.VIDEO
 
    def _sanitize_string_list(self, raw_list: Any) -> list[str]:
        if not raw_list or not isinstance(raw_list, list):
            return []
        return [item.strip() for item in raw_list if isinstance(item, str) and item.strip()]
 