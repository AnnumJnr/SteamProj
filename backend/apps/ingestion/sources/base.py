"""
Base ingestion source.

Defines the abstract interface that every ingestion source must implement.
All sources (YouTube, freeCodeCamp, MIT OCW, OpenStax, CK-12) extend this class.

Rule 13 (build order): This is the foundation. Every source file imports from here.
Rule 14: One responsibility per class — this class defines the contract only.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ─── Raw Course Data Container ────────────────────────────────────────────────

@dataclass
class RawCourse:
    """
    Intermediate container for raw data fetched from a source.

    This is the output of every source fetcher and the input to the normalizer.
    All fields are deliberately permissive (Any / str / None) because raw source
    data is unvalidated. The normalizer converts this into the validated internal
    schema.

    Rule 14: Fetch produces RawCourse. Normalizer consumes RawCourse.
    These are two separate responsibilities.
    """

    # Required by all sources
    external_id: str                        # Unique ID within the source system
    title: str                              # Raw title from source
    source_url: str                         # Canonical URL on the source platform
    provider: str                           # Must match Course.Provider choices

    # Descriptive fields — may be empty strings, never None after normalizer
    short_description: str = ""
    full_description: str = ""
    instructor: str = ""
    thumbnail_url: str = ""
    language: str = "en"

    # Classification — normalizer will validate against Course choices
    category: str = ""
    sub_category: str = ""
    level: str = ""                         # Beginner | Intermediate | Advanced
    age_group: str = ""                     # Kids | Teens | Adults
    format: str = ""                        # Video | Text | Interactive

    # Duration
    duration_hours: int = 0
    duration_minutes: int = 0

    # Ratings from source
    rating_average: float = 0.0
    rating_count: int = 0

    # Structured content
    tags: list = field(default_factory=list)
    learning_outcomes: list = field(default_factory=list)
    prerequisites: list = field(default_factory=list)

    # Flags
    is_free: bool = True
    certificate_available: bool = False

    # Source-specific raw payload — preserved verbatim in source_metadata
    raw_payload: dict = field(default_factory=dict)


# ─── Fetch Result Container ───────────────────────────────────────────────────

@dataclass
class FetchResult:
    """
    Output of a source fetch operation.

    Wraps the list of RawCourses with metadata about the fetch itself.
    The pipeline reads this to decide whether to proceed, log a fallback, or abort.

    Rule 8: Every fetch result carries enough context for observability.
    """

    source: str                             # IngestionLog.Source value
    courses: list[RawCourse] = field(default_factory=list)
    success: bool = True
    fallback_triggered: bool = False
    fallback_reason: str = ""
    error_message: str = ""
    raw_count: int = 0                      # Total items seen before filtering


# ─── Abstract Base Source ─────────────────────────────────────────────────────

class BaseIngestionSource(ABC):
    """
    Abstract base class for all ingestion sources.

    Every source must implement:
    - source_name: the IngestionLog.Source string identifier
    - fetch(): retrieve raw data from the external API and return a FetchResult

    The base class provides:
    - _build_raw_course(): safe construction helper
    - _handle_fetch_error(): standardized error logging and FetchResult construction

    Rule 3: Sources only fetch. Pipeline calls fetch(). Normalizer cleans.
    Rule 9: No hidden side effects — fetch() never writes to the DB.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        The IngestionLog.Source identifier for this source.
        Must match one of IngestionLog.Source choices exactly.
        e.g. 'youtube', 'freecodecamp', 'mit_ocw', 'openstax', 'ck12'
        """
        ...

    @abstractmethod
    def fetch(self) -> FetchResult:
        """
        Fetch raw course data from the external source.

        Must return a FetchResult in all cases — never raise an unhandled exception.
        If the fetch fails entirely, return a FetchResult with success=False.

        Rule 9: This method must not write to the DB, fire events, or send emails.
        Rule 2: If a fallback is used, set fallback_triggered=True and fallback_reason.
        """
        ...

    def _handle_fetch_error(
        self,
        error: Exception,
        context: str = "",
    ) -> FetchResult:
        """
        Standardized error handler for fetch failures.

        Logs the error at ERROR level and returns a failed FetchResult.
        Called inside fetch() implementations when an unrecoverable error occurs.

        Rule 8: Observability — every failure is logged with context.
        Rule 2: No silent fallbacks — failure is explicit.
        """
        message = f"{self.__class__.__name__}.fetch error"
        if context:
            message += f" [{context}]"
        message += f": {type(error).__name__}: {error}"

        logger.error(message)

        return FetchResult(
            source=self.source_name,
            success=False,
            error_message=str(error),
        )

    def _build_raw_course(self, **kwargs) -> RawCourse:
        """
        Safe constructor for RawCourse.

        Wraps the dataclass constructor so that subclasses get consistent
        construction with logging if required fields are missing.

        Rule 13 (clarity): Prefer explicit construction with this helper
        over direct RawCourse() calls in subclasses.
        """
        required = ["external_id", "title", "source_url", "provider"]
        missing = [f for f in required if not kwargs.get(f)]

        if missing:
            logger.warning(
                "%s._build_raw_course: Missing required fields %s — course may fail normalizer.",
                self.__class__.__name__,
                missing,
            )

        return RawCourse(**kwargs)