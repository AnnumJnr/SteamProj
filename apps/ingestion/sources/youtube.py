"""
YouTube ingestion source.

Fetches STEM course/playlist data from the YouTube Data API v3.

API constraints (master reference §2):
- 10,000 unit quota per day — each search.list call costs 100 units,
  each playlistItems.list call costs 1 unit.
- Incremental / scheduled nightly batches to stay within quota.
- Embed-first display; redirect fallback if embed is blocked.

Quota budget per run (default):
- Up to 50 search queries × 100 units = 5,000 units
- Remaining budget used for playlist detail calls (1 unit each)
- Conservative default: 10 queries per run to leave headroom for other systems.

Changes from Phase 3:
- _item_to_raw_course() now extracts defaultAudioLanguage and defaultLanguage
  from the snippet and stores them in raw_payload under 'audio_language' and
  'default_language'. These are passed to the normalizer's language detection
  pipeline via the RawCourse.language field and raw_payload.
- defaultAudioLanguage is preferred over defaultLanguage because it reflects
  the actual spoken language of the content, not just the metadata language.
  YouTube populates this field when the channel owner tags their audio language.

Rule 2: Every fallback is documented with full comment block.
Rule 8: Every fetch step is logged.
Rule 14: This file fetches only — normalizer handles transformation.
"""

import logging
from typing import Any

import requests
from django.conf import settings

from apps.ingestion.sources.base import BaseIngestionSource, FetchResult, RawCourse

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_PROVIDER = "YouTube"

# Search terms used to find STEM playlists and course series.
# These are intentionally broad — the normalizer applies category mapping.
STEM_SEARCH_QUERIES = [
    "python programming tutorial course",
    "mathematics lecture series",
    "physics course for beginners",
    "chemistry tutorial series",
    "biology lecture course",
    "computer science fundamentals",
    "engineering basics tutorial",
    "algebra mathematics course",
    "calculus tutorial series",
    "data science beginner course",
]

# Max results per search query (YouTube API max is 50, costs 100 units per call)
RESULTS_PER_QUERY = 10

# Request timeout in seconds
REQUEST_TIMEOUT = 15


class YouTubeIngestionSource(BaseIngestionSource):
    """
    Fetches STEM playlists from YouTube Data API v3.

    Strategy: Search for STEM-related playlists, then fetch basic metadata
    for each. Playlists are used rather than individual videos because they
    map more cleanly to the concept of a structured "course."

    Quota awareness:
    - search.list: 100 units per call
    - playlists.list: 1 unit per call
    - We run at most len(STEM_SEARCH_QUERIES) search calls per batch.

    Rule 14: fetch() fetches. normalizer.py transforms.
    Rule 9: fetch() never writes to the database.
    """

    @property
    def source_name(self) -> str:
        return "youtube"

    def fetch(self) -> FetchResult:
        """
        Fetch STEM playlists from YouTube Data API v3.

        Flow:
        1. Validate API key is configured
        2. Execute search queries to find STEM playlists
        3. Fetch playlist details for each result
        4. Build RawCourse objects
        5. Return FetchResult

        Rule 2: If API key is missing, return failed FetchResult — no silent skip.
        Rule 8: Log counts at each stage.
        """
        api_key = settings.YOUTUBE_API_KEY

        if not api_key:
            logger.error(
                "YouTubeIngestionSource.fetch: YOUTUBE_API_KEY is not configured. "
                "Set this in your .env file. Ingestion aborted."
            )
            return FetchResult(
                source=self.source_name,
                success=False,
                error_message="YOUTUBE_API_KEY not configured.",
            )

        logger.info(
            "YouTubeIngestionSource.fetch: Starting. Queries=%d, ResultsPerQuery=%d",
            len(STEM_SEARCH_QUERIES),
            RESULTS_PER_QUERY,
        )

        try:
            playlist_ids = self._search_playlists(api_key)
        except Exception as exc:
            return self._handle_fetch_error(exc, context="search_playlists")

        if not playlist_ids:
            logger.warning(
                "YouTubeIngestionSource.fetch: Search returned zero playlist IDs. "
                "Check API key validity and quota usage."
            )
            return FetchResult(
                source=self.source_name,
                success=True,
                courses=[],
                raw_count=0,
            )

        logger.info(
            "YouTubeIngestionSource.fetch: Found %d unique playlists. Fetching details.",
            len(playlist_ids),
        )

        try:
            raw_courses = self._fetch_playlist_details(api_key, playlist_ids)
        except Exception as exc:
            return self._handle_fetch_error(exc, context="fetch_playlist_details")

        logger.info(
            "YouTubeIngestionSource.fetch: Complete. raw_count=%d, built=%d",
            len(playlist_ids),
            len(raw_courses),
        )

        return FetchResult(
            source=self.source_name,
            courses=raw_courses,
            success=True,
            raw_count=len(playlist_ids),
        )

    # ─── Private: Search ──────────────────────────────────────────────────────

    def _search_playlists(self, api_key: str) -> list[str]:
        """
        Run all STEM search queries and collect unique playlist IDs.

        Returns a deduplicated list of playlist IDs.
        Each search.list call costs 100 quota units.

        Rule 14: Searches only. Returns IDs for the detail fetch step.
        """
        seen_ids: set[str] = set()
        playlist_ids: list[str] = []

        for query in STEM_SEARCH_QUERIES:
            try:
                ids = self._search_single_query(api_key, query)
                new_ids = [pid for pid in ids if pid not in seen_ids]
                seen_ids.update(new_ids)
                playlist_ids.extend(new_ids)

                logger.debug(
                    "YouTubeIngestionSource._search_playlists: "
                    "query='%s' → %d results (%d new)",
                    query,
                    len(ids),
                    len(new_ids),
                )
            except Exception as exc:
                # Per-query failure is non-fatal — log and continue with remaining queries
                # FALLBACK: Skip failed query, continue with remaining queries
                # PRIMARY: apps/ingestion/sources/youtube.py → _search_single_query()
                # CONDITION: HTTP error or timeout on a single search query
                # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → investigate primary
                logger.warning(
                    "YouTubeIngestionSource._search_playlists: Query '%s' failed: %s. "
                    "Continuing with remaining queries.",
                    query,
                    exc,
                )

        return playlist_ids

    def _search_single_query(self, api_key: str, query: str) -> list[str]:
        """
        Execute one YouTube search.list API call for STEM playlists.

        Returns list of playlist IDs (not full objects — detail fetch is separate).
        Costs 100 quota units per call.

        Rule 14: One job — returns raw playlist IDs only.
        """
        params = {
            "key": api_key,
            "q": query,
            "type": "playlist",
            "part": "id",
            "maxResults": RESULTS_PER_QUERY,
            "relevanceLanguage": "en",
            "safeSearch": "strict",
        }

        response = requests.get(
            f"{YOUTUBE_API_BASE}/search",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        return [
            item["id"]["playlistId"]
            for item in data.get("items", [])
            if item.get("id", {}).get("playlistId")
        ]

    # ─── Private: Detail Fetch ────────────────────────────────────────────────

    def _fetch_playlist_details(
        self, api_key: str, playlist_ids: list[str]
    ) -> list[RawCourse]:
        """
        Fetch full metadata for each playlist ID via playlists.list API.

        YouTube allows up to 50 IDs per playlists.list call (1 quota unit each batch).
        We batch in groups of 50.

        Rule 14: Detail fetch only — no transformation of values here.
        """
        raw_courses: list[RawCourse] = []

        batch_size = 50
        batches = [
            playlist_ids[i : i + batch_size]
            for i in range(0, len(playlist_ids), batch_size)
        ]

        for batch_index, batch in enumerate(batches):
            try:
                batch_results = self._fetch_playlist_batch(api_key, batch)
                raw_courses.extend(batch_results)

                logger.debug(
                    "YouTubeIngestionSource._fetch_playlist_details: "
                    "Batch %d/%d — fetched %d playlists.",
                    batch_index + 1,
                    len(batches),
                    len(batch_results),
                )
            except Exception as exc:
                # Per-batch failure is non-fatal — log and continue
                # FALLBACK: Skip failed batch, continue with remaining batches
                # PRIMARY: apps/ingestion/sources/youtube.py → _fetch_playlist_batch()
                # CONDITION: HTTP error or timeout on a single batch request
                # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → investigate primary
                logger.warning(
                    "YouTubeIngestionSource._fetch_playlist_details: "
                    "Batch %d failed: %s. Skipping batch.",
                    batch_index + 1,
                    exc,
                )

        return raw_courses

    def _fetch_playlist_batch(
        self, api_key: str, playlist_ids: list[str]
    ) -> list[RawCourse]:
        """
        Fetch details for a batch of up to 50 playlist IDs.

        Calls playlists.list with snippet and contentDetails parts.
        snippet already contains defaultAudioLanguage and defaultLanguage
        — no additional API part or quota cost is needed to get these fields.
        Costs 1 quota unit per call regardless of IDs in the batch.

        Rule 9: Builds RawCourse objects only — no DB writes, no events.
        """
        params = {
            "key": api_key,
            "id": ",".join(playlist_ids),
            # snippet contains: title, description, channelTitle, thumbnails,
            # defaultLanguage, defaultAudioLanguage — all retrieved in one call.
            "part": "snippet,contentDetails",
        }

        response = requests.get(
            f"{YOUTUBE_API_BASE}/playlists",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        raw_courses = []
        for item in data.get("items", []):
            raw_course = self._item_to_raw_course(item)
            if raw_course:
                raw_courses.append(raw_course)

        return raw_courses

    def _item_to_raw_course(self, item: dict[str, Any]) -> RawCourse | None:
        """
        Convert a single YouTube playlist API item into a RawCourse.

        Returns None if required fields are missing (malformed API response).

        Language field resolution order:
          1. defaultAudioLanguage — reflects the actual spoken language of the
             content. Most reliable signal. Set by channel owners who tag their
             audio language in YouTube Studio.
          2. defaultLanguage — the language of the playlist's metadata (title
             and description). Less reliable than audio language.
          3. Empty string — not set by the channel owner. The normalizer will
             treat this as unknown and apply the thin-content penalty if the
             title and description are also uninformative.

        Both audio_language and default_language are stored in raw_payload so
        the normalizer's language pipeline can access them directly from
        source_metadata after ingestion.

        Rule 9: No hidden logic — extraction only, no business decisions.
        Rule 13: Explicit over clever — direct field access, no magic.
        """
        playlist_id = item.get("id")
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})

        if not playlist_id or not snippet.get("title"):
            logger.warning(
                "YouTubeIngestionSource._item_to_raw_course: "
                "Skipping item with missing id or title: %s",
                item,
            )
            return None

        title = snippet.get("title", "")
        description = snippet.get("description", "")
        channel_title = snippet.get("channelTitle", "")
        thumbnails = snippet.get("thumbnails", {})

        # Prefer high-res thumbnail; fall back through available sizes
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )

        item_count = content_details.get("itemCount", 0)
        source_url = f"https://www.youtube.com/playlist?list={playlist_id}"

        # ── Language metadata extraction ──────────────────────────────────────
        # Both fields live in snippet and are already returned by the API call
        # above — no additional quota cost.
        #
        # defaultAudioLanguage: the spoken/audio language of the playlist content.
        #   YouTube uses BCP-47 tags e.g. 'en', 'hi', 'ar', 'ur'.
        #   Not all channel owners set this — absence means unknown, not English.
        #
        # defaultLanguage: the language of the playlist title and description.
        #   Less useful for our purpose but stored as a secondary signal.
        audio_language = snippet.get("defaultAudioLanguage", "") or ""
        default_language = snippet.get("defaultLanguage", "") or ""

        # Pass the most reliable language signal as the RawCourse.language field.
        # The normalizer reads this as Layer 1 of the language detection pipeline.
        # Preference: audio > default > empty (unknown).
        raw_language = audio_language or default_language or ""

        logger.debug(
            "YouTubeIngestionSource._item_to_raw_course: "
            "playlist_id=%s audio_language='%s' default_language='%s'",
            playlist_id,
            audio_language,
            default_language,
        )

        return self._build_raw_course(
            external_id=playlist_id,
            title=title,
            short_description=description[:300] if description else "",
            full_description=description,
            source_url=source_url,
            provider=YOUTUBE_PROVIDER,
            instructor=channel_title,
            thumbnail_url=thumbnail_url,
            language=raw_language,    # Now carries actual audio/metadata language
            format="Video",
            category="",
            level="",
            age_group="",
            tags=[],
            raw_payload={
                "playlist_id": playlist_id,
                "snippet": snippet,
                "content_details": content_details,
                "item_count": item_count,
                # Stored explicitly for direct access in source_metadata
                # after ingestion — used by flag_language_status command
                # when re-screening existing courses.
                "audio_language": audio_language,
                "default_language": default_language,
            },
        )