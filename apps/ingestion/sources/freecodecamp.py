"""
freeCodeCamp ingestion source.

freeCodeCamp restructured their entire curriculum in 2024-2025. The old
meta.json files at curriculum/challenges/english/<superblock>/ no longer exist.
The repo now uses a block-level structure under curriculum/challenges/_meta/
and introduced a new "full-stack-developer" superblock replacing the old ones.

Fix approach: freeCodeCamp's certifications are a small, stable, well-known set.
Rather than crawling their repo structure (which changes), we define each
certification as a static entry and verify the course URL is live before
building the RawCourse. This is more reliable than repo parsing and matches
how freeCodeCamp themselves present their curriculum — as a fixed set of
named certifications on freecodecamp.org/learn.

License: MIT — open-source curriculum, legal to use and attribute.

Rule 2: Fallback documented with full comment block.
Rule 8: Every step logged.
Rule 14: Fetch only — normalizer transforms.
"""

import logging

import requests

from apps.ingestion.sources.base import BaseIngestionSource, FetchResult, RawCourse

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

FCC_PROVIDER = "freeCodeCamp"
FCC_LEARN_BASE = "https://www.freecodecamp.org/learn"
REQUEST_TIMEOUT = 15

# Static certification registry.
#
# freeCodeCamp's certifications are a curated, stable set maintained by their
# core team. This list reflects their current curriculum as of 2025:
# https://www.freecodecamp.org/learn
#
# Fields: (slug, display_name, stem_category, description, duration_hours)
# Slug corresponds to the URL path: freecodecamp.org/learn/<slug>
#
# Update this list when freeCodeCamp announces new certifications.
# Retired certifications should be removed — their courses will become
# inactive on the next ingestion run via the upsert logic in services.py.

STEM_CERTIFICATIONS = [
    (
        "full-stack-developer",
        "Full Stack Developer",
        "Computer Science",
        "Learn HTML, CSS, JavaScript, React, Node.js, Python, SQL, and more "
        "in this comprehensive full stack development curriculum.",
        1800,
    ),
    (
        "scientific-computing-with-python",
        "Scientific Computing with Python",
        "Computer Science",
        "Learn Python fundamentals, data structures, algorithms, and scientific "
        "computing concepts including NumPy and data analysis.",
        300,
    ),
    (
        "data-analysis-with-python",
        "Data Analysis with Python",
        "Computer Science",
        "Learn data analysis with Python using Pandas, NumPy, Matplotlib, "
        "Seaborn, and Jupyter Notebook.",
        300,
    ),
    (
        "machine-learning-with-python",
        "Machine Learning with Python",
        "Computer Science",
        "Learn machine learning fundamentals with Python using TensorFlow "
        "and scikit-learn. Build neural networks and ML algorithms.",
        300,
    ),
    (
        "college-algebra-with-python",
        "College Algebra with Python",
        "Mathematics",
        "Learn college algebra concepts using Python as a calculation tool. "
        "Covers equations, functions, graphs, and algebraic reasoning.",
        200,
    ),
    (
        "foundational-c-sharp-with-microsoft",
        "Foundational C# with Microsoft",
        "Computer Science",
        "Learn C# programming fundamentals in partnership with Microsoft. "
        "Covers syntax, object-oriented programming, and .NET basics.",
        200,
    ),
    (
        "javascript-algorithms-and-data-structures",
        "JavaScript Algorithms and Data Structures",
        "Computer Science",
        "Learn JavaScript fundamentals, ES6, regular expressions, debugging, "
        "data structures, and algorithm scripting.",
        300,
    ),
    (
        "responsive-web-design",
        "Responsive Web Design",
        "Technology & Applied Skills",
        "Learn HTML and CSS to build responsive websites. Covers flexbox, "
        "CSS Grid, and accessibility best practices.",
        300,
    ),
    (
        "front-end-development-libraries",
        "Front End Development Libraries",
        "Computer Science",
        "Learn React, Redux, jQuery, Bootstrap, and Sass to build interactive "
        "front end web applications.",
        300,
    ),
    (
        "data-visualization",
        "Data Visualization",
        "Computer Science",
        "Learn D3.js to create dynamic data visualizations. Build bar charts, "
        "scatter plots, heat maps, and choropleth maps.",
        300,
    ),
    (
        "back-end-development-and-apis",
        "Back End Development and APIs",
        "Computer Science",
        "Learn Node.js, Express, MongoDB, and Mongoose to build back end web "
        "applications and REST APIs.",
        300,
    ),
    (
        "quality-assurance",
        "Quality Assurance",
        "Computer Science",
        "Learn software testing with Chai, Node.js, and Express. Build test "
        "suites and practice test-driven development.",
        300,
    ),
    (
        "information-security",
        "Information Security",
        "Computer Science",
        "Learn cybersecurity fundamentals, penetration testing with HelmetJS, "
        "and build a secure real-time messaging application.",
        300,
    ),
]


class FreecodeCAmpIngestionSource(BaseIngestionSource):
    """
    Builds RawCourse objects for freeCodeCamp certifications.

    Uses a static certification registry rather than repo parsing because
    freeCodeCamp's repo structure changed in 2024-2025, making path-based
    meta.json fetching unreliable. The certification set is small (13 items),
    stable, and maintained by the freeCodeCamp core team.

    Each certification URL is verified to be live before creating a RawCourse.
    A 404 means the certification was renamed or retired — logged and skipped.

    Rule 14: fetch() builds RawCourse objects. normalizer.py transforms.
    Rule 9: fetch() never writes to the DB.
    """

    @property
    def source_name(self) -> str:
        return "freecodecamp"

    def fetch(self) -> FetchResult:
        """
        Build RawCourse objects for each freeCodeCamp STEM certification.

        Flow:
        1. Iterate STEM_CERTIFICATIONS registry
        2. Verify the course URL is live (HEAD request)
        3. Build RawCourse for each live certification
        4. Return FetchResult

        URL verification uses HEAD (not GET) to avoid downloading page content.
        A non-200 response means the slug has changed — logged and skipped.

        Rule 8: Counts logged at completion.
        """
        logger.info(
            "FreecodeCAmpIngestionSource.fetch: Starting. Certifications=%d",
            len(STEM_CERTIFICATIONS),
        )

        raw_courses: list[RawCourse] = []
        skipped = 0

        for slug, name, category, description, duration_hours in STEM_CERTIFICATIONS:
            try:
                source_url = f"{FCC_LEARN_BASE}/{slug}"
                is_live = self._verify_url(source_url)

                if not is_live:
                    # FALLBACK: Skip certification with dead URL, continue with remaining
                    # PRIMARY: apps/ingestion/sources/freecodecamp.py → STEM_CERTIFICATIONS
                    # CONDITION: freeCodeCamp renamed or retired a certification slug
                    # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → update STEM_CERTIFICATIONS
                    logger.warning(
                        "FreecodeCAmpIngestionSource.fetch: URL not live for '%s' at %s. "
                        "Certification may have been renamed. Update STEM_CERTIFICATIONS.",
                        slug,
                        source_url,
                    )
                    skipped += 1
                    continue

                raw_course = self._build_raw_course(
                    external_id=f"fcc-{slug}",
                    title=name,
                    short_description=description[:300],
                    full_description=description,
                    source_url=source_url,
                    provider=FCC_PROVIDER,
                    instructor="freeCodeCamp",
                    thumbnail_url="",
                    format="Interactive",
                    category=category,
                    level="",
                    age_group="",
                    is_free=True,
                    certificate_available=True,
                    duration_hours=duration_hours,
                    tags=["freeCodeCamp", slug.replace("-", " ")],
                    raw_payload={
                        "slug": slug,
                        "certification_name": name,
                        "stem_category": category,
                    },
                )
                raw_courses.append(raw_course)

                logger.debug(
                    "FreecodeCAmpIngestionSource.fetch: Built certification '%s'.", name,
                )

            except Exception as exc:
                # FALLBACK: Skip failed certification, continue with remaining
                # PRIMARY: apps/ingestion/sources/freecodecamp.py → fetch()
                # CONDITION: Network error verifying a single certification URL
                # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → investigate network
                logger.warning(
                    "FreecodeCAmpIngestionSource.fetch: Failed on '%s': %s. Skipping.",
                    slug,
                    exc,
                )
                skipped += 1

        logger.info(
            "FreecodeCAmpIngestionSource.fetch: Complete. built=%d, skipped=%d",
            len(raw_courses),
            skipped,
        )

        return FetchResult(
            source=self.source_name,
            courses=raw_courses,
            success=True,
            raw_count=len(STEM_CERTIFICATIONS),
        )

    def _verify_url(self, url: str) -> bool:
        """
        Verify a freeCodeCamp certification URL is live using a HEAD request.

        Returns True if the server responds with 200, False otherwise.
        HEAD requests do not download page content — safe for quota/rate limits.

        Rule 14: One job — check if URL is live. Returns bool only.
        """
        try:
            response = requests.head(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False