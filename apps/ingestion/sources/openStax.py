"""
OpenStax ingestion source.

Fetches open textbook data from the OpenStax CMS API.

Confirmed working endpoint (from official OpenStax CMS API wiki):
  GET https://openstax.org/apps/cms/api/books

Returns a list of all published books with slug, title, subjects,
cover_url, and author metadata. No pagination — single response.
No API key required.

License: Creative Commons — open textbooks, free to use and attribute.

Master reference §2:
- Method: API
- Role: Primary foundational STEM source
- Provider name stored: "OpenStax"

Rule 2: Fallback documented with full comment block.
Rule 8: Every step logged.
Rule 14: Fetch only — normalizer transforms.
"""

import logging
from typing import Any

import requests

from apps.ingestion.sources.base import BaseIngestionSource, FetchResult, RawCourse

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

OPENSTAX_PROVIDER = "OpenStax"
OPENSTAX_BASE = "https://openstax.org"

# Confirmed correct endpoint from https://github.com/openstax/openstax-cms/wiki/API-Endpoints
# Returns a list of all published books. No pagination. No auth required.
OPENSTAX_BOOKS_API = f"{OPENSTAX_BASE}/apps/cms/api/books"
OPENSTAX_BOOK_DETAIL_BASE = f"{OPENSTAX_BASE}/details"

REQUEST_TIMEOUT = 20

# Subject name → STEM category mapping.
# These match the subject names returned by the OpenStax books API exactly.
STEM_SUBJECT_MAP: dict[str, str] = {
    "Math": "Mathematics",
    "Mathematics": "Mathematics",
    "Science": "Natural Sciences",
    "Physics": "Natural Sciences",
    "Biology": "Natural Sciences",
    "Chemistry": "Natural Sciences",
    "Anatomy & Physiology": "Natural Sciences",
    "Statistics": "Mathematics",
    "Computer Science": "Computer Science",
    "Engineering": "Engineering",
}


class OpenStaxIngestionSource(BaseIngestionSource):
    """
    Fetches open textbooks from the OpenStax CMS API.

    The /apps/cms/api/books endpoint returns all published books in a
    single JSON response — no pagination required. We filter client-side
    to STEM subjects only.

    Rule 14: fetch() fetches. normalizer.py transforms.
    Rule 9: fetch() never writes to the DB.
    """

    @property
    def source_name(self) -> str:
        return "openstax"

    def fetch(self) -> FetchResult:
        """
        Fetch all STEM books from the OpenStax books API.

        Flow:
        1. GET /apps/cms/api/books — single request, returns all books
        2. Filter to STEM subjects client-side
        3. Build RawCourse for each STEM book
        4. Return FetchResult

        Rule 8: Counts logged at completion.
        Rule 2: API failure returns failed FetchResult — no silent skip.
        """
        logger.info(
            "OpenStaxIngestionSource.fetch: Starting. API=%s",
            OPENSTAX_BOOKS_API,
        )

        try:
            all_books = self._fetch_all_books()
        except Exception as exc:
            return self._handle_fetch_error(exc, context="fetch_all_books")

        logger.info(
            "OpenStaxIngestionSource.fetch: Retrieved %d total books. Filtering for STEM.",
            len(all_books),
        )

        raw_courses: list[RawCourse] = []
        skipped = 0

        for book in all_books:
            try:
                stem_category = self._get_stem_category(book)
                if not stem_category:
                    skipped += 1
                    continue

                raw_course = self._book_to_raw_course(book, stem_category)
                if raw_course:
                    raw_courses.append(raw_course)
                else:
                    skipped += 1

            except Exception as exc:
                # FALLBACK: Skip malformed book entry, continue with remaining
                # PRIMARY: apps/ingestion/sources/openStax.py → _book_to_raw_course()
                # CONDITION: Malformed or unexpected field structure in one book entry
                # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → investigate primary
                logger.warning(
                    "OpenStaxIngestionSource.fetch: Failed to parse book '%s': %s. Skipping.",
                    book.get("title", "unknown"),
                    exc,
                )
                skipped += 1

        logger.info(
            "OpenStaxIngestionSource.fetch: Complete. raw_count=%d, built=%d, skipped=%d",
            len(all_books),
            len(raw_courses),
            skipped,
        )

        return FetchResult(
            source=self.source_name,
            courses=raw_courses,
            success=True,
            raw_count=len(all_books),
        )

    # ─── Private: API Fetch ───────────────────────────────────────────────────

    def _fetch_all_books(self) -> list[dict[str, Any]]:
        """
        Fetch the full book list from the confirmed /apps/cms/api/books endpoint.

        This endpoint returns all books in a single JSON array — no pagination.
        Confirmed from: https://github.com/openstax/openstax-cms/wiki/API-Endpoints

        Rule 14: One HTTP request. Returns raw list of book dicts.
        """
        response = requests.get(
            OPENSTAX_BOOKS_API,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        # The endpoint returns a plain JSON array of book objects
        if isinstance(data, list):
            return data

        # Handle wrapped responses as a safety net
        if isinstance(data, dict):
            for key in ("books", "results", "items", "data"):
                if key in data and isinstance(data[key], list):
                    return data[key]

        logger.warning(
            "OpenStaxIngestionSource._fetch_all_books: Unexpected response shape: %s",
            type(data).__name__,
        )
        return []

    # ─── Private: Category Detection ─────────────────────────────────────────

    def _get_stem_category(self, book: dict[str, Any]) -> str | None:
        """
        Determine the STEM category for a book from its subjects.

        Returns the STEM category string, or None if the book is not STEM
        (Humanities, Social Sciences, Business, etc.).
        """
        subjects = book.get("subjects", []) or []

        for subject in subjects:
            name = subject if isinstance(subject, str) else subject.get("name", "")
            if name in STEM_SUBJECT_MAP:
                return STEM_SUBJECT_MAP[name]

        # Also check top-level subject fields used by some API response shapes
        for field in ("subject_name", "subject"):
            name = book.get(field, "")
            if name and name in STEM_SUBJECT_MAP:
                return STEM_SUBJECT_MAP[name]

        return None

    # ─── Private: Item Transformation ─────────────────────────────────────────

    def _book_to_raw_course(
        self,
        book: dict[str, Any],
        stem_category: str,
    ) -> RawCourse | None:
        """
        Convert a single OpenStax book entry into a RawCourse.

        Rule 9: Extraction only — no business decisions.
        Rule 13: Explicit field access.
        """
        book_id = book.get("id")
        title = (book.get("title") or "").strip()

        if not book_id or not title:
            logger.warning(
                "OpenStaxIngestionSource._book_to_raw_course: "
                "Skipping book missing id or title."
            )
            return None

        slug = book.get("slug", "") or ""
        source_url = f"{OPENSTAX_BOOK_DETAIL_BASE}/{slug}" if slug else ""
        if not source_url:
            logger.warning(
                "OpenStaxIngestionSource._book_to_raw_course: No slug for '%s'. Skipping.",
                title,
            )
            return None

        description = self._strip_basic_html(book.get("description", "") or "")
        short_description = description[:300] if description else f"OpenStax open textbook: {title}."

        authors = book.get("authors", []) or []
        instructor = self._format_authors(authors)

        # Cover image — try multiple field names
        cover_url = ""
        if book.get("cover_url"):
            cover_url = book["cover_url"]
        elif isinstance(book.get("cover"), dict):
            cover_url = book["cover"].get("url", "")

        subjects = book.get("subjects", []) or []
        tags = ["openstax", "open textbook"]
        for s in subjects:
            name = s if isinstance(s, str) else s.get("name", "")
            if name:
                tags.append(name.lower())

        return self._build_raw_course(
            external_id=f"openstax-{book_id}",
            title=title,
            short_description=short_description,
            full_description=description,
            source_url=source_url,
            provider=OPENSTAX_PROVIDER,
            instructor=instructor,
            thumbnail_url=cover_url,
            format="Text",
            category=stem_category,
            sub_category="",
            level="",
            age_group="Adults",
            is_free=True,
            certificate_available=False,
            tags=list(set(tags)),
            raw_payload={
                "openstax_id": book_id,
                "slug": slug,
                "subjects": subjects,
                "authors": authors,
                "book": book,
            },
        )

    # ─── Private: Helpers ─────────────────────────────────────────────────────

    def _format_authors(self, authors: list) -> str:
        """Format OpenStax author list into a display string."""
        if not authors:
            return "OpenStax"
        names = []
        for author in authors:
            name = author if isinstance(author, str) else author.get("name", "")
            if name:
                names.append(name.strip())
        return ", ".join(names[:3]) if names else "OpenStax"

    def _strip_basic_html(self, text: str) -> str:
        """Remove simple HTML tags from description text."""
        if not text or "<" not in text:
            return text
        result = []
        in_tag = False
        for char in text:
            if char == "<":
                in_tag = True
            elif char == ">":
                in_tag = False
                result.append(" ")
            elif not in_tag:
                result.append(char)
        return " ".join("".join(result).split())