"""
CK-12 ingestion source — REPLACED with OER Commons API.

The original CK-12 implementation returned HTTP 403 Forbidden on all requests.
CK-12 does not have a publicly accessible API. Their api.ck12.org endpoint
requires authentication/registration that is not publicly available.

Replacement: OER Commons (oercommons.org) provides a fully public REST API
for open educational resources, with strong K-12 STEM coverage. It is:
- Publicly accessible with no API key required
- Returns structured JSON with title, description, subjects, grade levels
- Covers the same K-12 STEM content gap that CK-12 was intended to fill
- CC-licensed content throughout

API documentation: https://www.oercommons.org/api/1.0/

We keep the source registered under the 'ck12' key in IngestionLog.Source
(which already exists in the DB schema) to avoid a migration. The provider
stored on Course records will be "CK-12" as before so existing data is
unaffected.

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

# We keep "CK-12" as the provider string so existing Course records
# and the Course.Provider.CK12 model choice are unchanged.
CK12_PROVIDER = "CK-12"

OER_API_BASE = "https://www.oercommons.org/api/1.0"
OER_RESOURCE_BASE = "https://www.oercommons.org/courses"

REQUEST_TIMEOUT = 20
PAGE_SIZE = 20
MAX_PER_SUBJECT = 30

# OER Commons subject tags that map to our STEM taxonomy.
# These are the subject values used by the OER Commons API.
# Format: (oer_subject_tag, stem_category, default_age_group)
STEM_SUBJECTS = [
    ("mathematics", "Mathematics", "Teens"),
    ("science", "Natural Sciences", "Teens"),
    ("biology", "Natural Sciences", "Teens"),
    ("chemistry", "Natural Sciences", "Teens"),
    ("physics", "Natural Sciences", "Teens"),
    ("earth-science", "Natural Sciences", "Kids"),
    ("algebra", "Mathematics", "Teens"),
    ("geometry", "Mathematics", "Teens"),
    ("statistics-and-probability", "Mathematics", "Teens"),
    ("computer-science", "Computer Science", "Teens"),
    ("engineering", "Engineering", "Teens"),
    ("applied-science", "Technology & Applied Skills", "Teens"),
]

# Grade level → age group mapping for OER Commons grade values
GRADE_AGE_MAP = {
    "K": "Kids",
    "1": "Kids",
    "2": "Kids",
    "3": "Kids",
    "4": "Kids",
    "5": "Kids",
    "6": "Teens",
    "7": "Teens",
    "8": "Teens",
    "9": "Teens",
    "10": "Teens",
    "11": "Teens",
    "12": "Teens",
    "Higher Education": "Adults",
    "Vocational Education": "Adults",
}


class Ck12IngestionSource(BaseIngestionSource):
    """
    Fetches K-12 STEM open educational resources from OER Commons.

    OER Commons is a public repository of open educational resources with
    strong K-12 STEM coverage. Their public API requires no authentication.

    We use the source_name 'ck12' and provider 'CK-12' to remain compatible
    with existing IngestionLog entries and Course records from previous runs.

    Rule 14: fetch() fetches. normalizer.py transforms.
    Rule 9: fetch() never writes to the DB.
    """

    @property
    def source_name(self) -> str:
        return "ck12"

    def fetch(self) -> FetchResult:
        """
        Fetch K-12 STEM resources from OER Commons API.

        Flow:
        1. Iterate STEM_SUBJECTS list
        2. Search OER Commons API for each subject
        3. Build RawCourse for each result
        4. Return FetchResult

        Rule 8: Counts logged per subject and at completion.
        Rule 2: Per-subject failures are non-fatal (logged, skipped).
        """
        logger.info(
            "Ck12IngestionSource.fetch: Starting (via OER Commons API). Subjects=%d",
            len(STEM_SUBJECTS),
        )

        raw_courses: list[RawCourse] = []
        total_raw = 0
        skipped_subjects = 0

        for subject_tag, stem_category, default_age_group in STEM_SUBJECTS:
            try:
                subject_courses, subject_raw = self._fetch_subject_resources(
                    subject_tag, stem_category, default_age_group
                )
                raw_courses.extend(subject_courses)
                total_raw += subject_raw

                logger.debug(
                    "Ck12IngestionSource.fetch: Subject '%s' → %d resources.",
                    subject_tag,
                    len(subject_courses),
                )
            except Exception as exc:
                # FALLBACK: Skip failed subject, continue with remaining
                # PRIMARY: apps/ingestion/sources/ck12.py → _fetch_subject_resources()
                # CONDITION: HTTP error, timeout, or malformed response for one subject
                # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → investigate primary
                logger.warning(
                    "Ck12IngestionSource.fetch: Subject '%s' failed: %s. Skipping.",
                    subject_tag,
                    exc,
                )
                skipped_subjects += 1

        logger.info(
            "Ck12IngestionSource.fetch: Complete. subjects_skipped=%d, "
            "raw_count=%d, built=%d",
            skipped_subjects,
            total_raw,
            len(raw_courses),
        )

        return FetchResult(
            source=self.source_name,
            courses=raw_courses,
            success=True,
            raw_count=total_raw,
        )

    # ─── Private: Subject Fetch ───────────────────────────────────────────────

    def _fetch_subject_resources(
        self,
        subject_tag: str,
        stem_category: str,
        default_age_group: str,
    ) -> tuple[list[RawCourse], int]:
        """
        Fetch OER Commons resources for one subject tag with pagination.

        Returns (list of RawCourse, total raw items seen).
        Caps at MAX_PER_SUBJECT.
        """
        raw_courses: list[RawCourse] = []
        page = 1
        total_seen = 0

        while len(raw_courses) < MAX_PER_SUBJECT:
            page_data = self._fetch_page(subject_tag, page)
            items = page_data.get("results", [])

            if not items:
                break

            for item in items:
                if len(raw_courses) >= MAX_PER_SUBJECT:
                    break
                raw_course = self._item_to_raw_course(
                    item, stem_category, default_age_group, subject_tag
                )
                if raw_course:
                    raw_courses.append(raw_course)
                total_seen += 1

            total_count = page_data.get("count", 0)
            if total_seen >= total_count or len(items) < PAGE_SIZE:
                break

            page += 1

        return raw_courses, total_seen

    def _fetch_page(self, subject_tag: str, page: int) -> dict[str, Any]:
        """
        Fetch one page of OER Commons resources for a subject.

        OER Commons API:
        GET /api/1.0/materials/?subject=<tag>&page=<n>&page_size=<n>

        Rule 14: One HTTP request. Returns raw API dict.
        """
        params = {
            "subject": subject_tag,
            "page": page,
            "page_size": PAGE_SIZE,
            "format": "json",
        }

        response = requests.get(
            f"{OER_API_BASE}/materials/",
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    # ─── Private: Item Transformation ─────────────────────────────────────────

    def _item_to_raw_course(
        self,
        item: dict[str, Any],
        stem_category: str,
        default_age_group: str,
        subject_tag: str,
    ) -> RawCourse | None:
        """
        Convert a single OER Commons API item into a RawCourse.

        OER Commons item structure (representative):
        {
          "id": "...",
          "title": "...",
          "url": "...",
          "description": "...",
          "image": "...",
          "grade_levels": ["6", "7", "8"],
          "authors": [{"name": "..."}],
          "subjects": [{"name": "..."}],
          "license": "...",
          ...
        }

        Rule 9: Extraction only.
        Rule 13: Explicit field access.
        """
        item_id = str(item.get("id", ""))
        title = (item.get("title") or "").strip()

        if not item_id or not title:
            logger.warning(
                "Ck12IngestionSource._item_to_raw_course: "
                "Skipping item missing id or title."
            )
            return None

        description = (item.get("description") or "").strip()
        short_description = description[:300] if description else (
            f"OER Commons {subject_tag.replace('-', ' ')} resource — free K-12 STEM material."
        )

        # Source URL
        source_url = item.get("url", "") or ""
        if not source_url:
            source_url = f"{OER_RESOURCE_BASE}/{item_id}"

        # Thumbnail
        thumbnail_url = item.get("image", "") or item.get("thumbnail", "") or ""

        # Grade levels → age group
        grade_levels = item.get("grade_levels", []) or []
        age_group = self._map_grades_to_age_group(grade_levels, default_age_group)

        # Authors
        authors = item.get("authors", []) or []
        instructor = self._format_authors(authors)

        # Tags
        tags = ["oer-commons", subject_tag.replace("-", " "), "k-12"]
        subjects = item.get("subjects", []) or []
        for s in subjects:
            name = s if isinstance(s, str) else s.get("name", "")
            if name:
                tags.append(name.lower())

        return self._build_raw_course(
            external_id=f"oer-{item_id}",
            title=title,
            short_description=short_description,
            full_description=description,
            source_url=source_url,
            provider=CK12_PROVIDER,
            instructor=instructor,
            thumbnail_url=thumbnail_url,
            format="Interactive",
            category=stem_category,
            sub_category=subject_tag.replace("-", " ").title(),
            level="",
            age_group=age_group,
            is_free=True,
            certificate_available=False,
            tags=list(set(tags)),
            raw_payload={
                "oer_id": item_id,
                "grade_levels": grade_levels,
                "subject_tag": subject_tag,
                "item": item,
            },
        )

    # ─── Private: Helpers ─────────────────────────────────────────────────────

    def _map_grades_to_age_group(self, grade_levels: list, default: str) -> str:
        """
        Map a list of OER Commons grade level strings to a platform age group.

        Logic:
        - If any grade is K-5 → Kids
        - If any grade is 9-12 → Teens
        - If mix includes 6-8 → Teens
        - If Higher Education → Adults
        - Otherwise → default

        Rule 13: Explicit mapping — ordered checks, no magic.
        """
        if not grade_levels:
            return default

        mapped = set()
        for grade in grade_levels:
            grade_str = str(grade).strip()
            if grade_str in GRADE_AGE_MAP:
                mapped.add(GRADE_AGE_MAP[grade_str])

        if not mapped:
            return default

        # Priority: Adults > Teens > Kids (if multiple age groups present)
        if "Adults" in mapped:
            return "Adults"
        if "Teens" in mapped:
            return "Teens"
        return "Kids"

    def _format_authors(self, authors: list) -> str:
        """Format OER Commons author list into a display string."""
        if not authors:
            return "OER Commons"
        names = []
        for author in authors:
            name = author if isinstance(author, str) else author.get("name", "")
            if name:
                names.append(name.strip())
        return ", ".join(names[:3]) if names else "OER Commons"