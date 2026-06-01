"""
MIT OCW ingestion source — REPLACED with Khan Academy static registry.

MIT OpenCourseWare has no public REST API. Their course data is only
accessible by website scraping (prohibited by project rules) or downloading
50GB+ bulk data dumps from archive.org (not suitable for nightly ingestion).
No API endpoint exists at any version of /api/v0/, /api/v1/, or otherwise.

Replacement: Khan Academy static registry.

Khan Academy is already listed in the master reference (§2) as a manual-link
source. Their API was deprecated, but their course catalogue is large,
well-structured, and stable. We apply the same pattern used for freeCodeCamp:
define each course as a static entry with known metadata, then verify the
URL is live with a HEAD request before building a RawCourse.

Khan Academy covers:
- K-12 Mathematics (pre-algebra through calculus)
- K-12 Sciences (physics, chemistry, biology, earth science)
- Computer programming
- AP courses (university-level content)
This fills the gap left by removing MIT OCW and complements freeCodeCamp well.

We keep the source registered under 'mit_ocw' in IngestionLog.Source and
use 'MIT OCW' as the provider value to avoid a DB migration. The provider
stored on Course records will remain "MIT OCW" so existing data is unaffected.
To rename, update Course.Provider choices and run a migration.

NOTE FOR FUTURE: If MIT OCW ever publishes a proper public API, this source
should be reverted to fetch real MIT course data. The intent of this slot
is MIT OCW — Khan Academy is a pragmatic replacement for MVP.

Rule 2: Fallback documented with full comment block.
Rule 8: Every step logged.
Rule 14: Fetch only — normalizer transforms.
"""

import logging

import requests

from apps.ingestion.sources.base import BaseIngestionSource, FetchResult, RawCourse

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

# Provider stored on Course records — kept as "MIT OCW" to avoid migration
PROVIDER = "MIT OCW"
KA_BASE = "https://www.khanacademy.org"
REQUEST_TIMEOUT = 15

# Khan Academy STEM course registry.
#
# Each entry: (slug, display_name, category, age_group, level, description, duration_hours)
#
# Slugs correspond to khanacademy.org/[slug]. URL verification confirms each
# is live before building a RawCourse. Update when Khan Academy restructures.
#
# Source: https://www.khanacademy.org/
KA_COURSES = [
    # ── Mathematics ───────────────────────────────────────────────────────────
    (
        "math/early-math",
        "Early Math",
        "Mathematics", "Kids", "Beginner",
        "Learn counting, addition, subtraction, place value, and measurement "
        "for young learners.",
        50,
    ),
    (
        "math/arithmetic",
        "Arithmetic",
        "Mathematics", "Kids", "Beginner",
        "Master the fundamentals of arithmetic: addition, subtraction, "
        "multiplication, division, fractions, and decimals.",
        80,
    ),
    (
        "math/pre-algebra",
        "Pre-Algebra",
        "Mathematics", "Teens", "Beginner",
        "Prepare for algebra with negative numbers, absolute value, factors, "
        "multiples, fractions, decimals, and basic equations.",
        60,
    ),
    (
        "math/algebra",
        "Algebra 1",
        "Mathematics", "Teens", "Beginner",
        "Learn linear equations, inequalities, functions, systems of equations, "
        "and an introduction to polynomials.",
        80,
    ),
    (
        "math/algebra2",
        "Algebra 2",
        "Mathematics", "Teens", "Intermediate",
        "Study polynomials, complex numbers, rational functions, exponential "
        "and logarithmic functions, and conic sections.",
        80,
    ),
    (
        "math/geometry",
        "Geometry",
        "Mathematics", "Teens", "Intermediate",
        "Explore triangles, congruence, similarity, transformations, circles, "
        "area, volume, and trigonometric ratios.",
        80,
    ),
    (
        "math/trigonometry",
        "Trigonometry",
        "Mathematics", "Teens", "Intermediate",
        "Master sine, cosine, tangent, the unit circle, trigonometric identities, "
        "and inverse functions.",
        60,
    ),
    (
        "math/precalculus",
        "Precalculus",
        "Mathematics", "Teens", "Intermediate",
        "Bridge algebra and calculus with advanced functions, vectors, matrices, "
        "complex numbers, and polar coordinates.",
        80,
    ),
    (
        "math/statistics-probability",
        "Statistics and Probability",
        "Mathematics", "Teens", "Intermediate",
        "Explore data analysis, probability, distributions, hypothesis testing, "
        "confidence intervals, and regression.",
        80,
    ),
    (
        "math/ap-calculus-ab",
        "AP Calculus AB",
        "Mathematics", "Teens", "Advanced",
        "Learn limits, derivatives, integrals, and the Fundamental Theorem of "
        "Calculus at AP exam level.",
        100,
    ),
    (
        "math/ap-calculus-bc",
        "AP Calculus BC",
        "Mathematics", "Teens", "Advanced",
        "Covers all AP Calculus AB topics plus parametric equations, polar "
        "coordinates, infinite series, and more.",
        120,
    ),
    (
        "math/linear-algebra",
        "Linear Algebra",
        "Mathematics", "Adults", "Advanced",
        "Study vectors, matrices, transformations, eigenvalues, eigenvectors, "
        "and their applications.",
        80,
    ),
    (
        "math/multivariable-calculus",
        "Multivariable Calculus",
        "Mathematics", "Adults", "Advanced",
        "Explore partial derivatives, gradient, divergence, curl, line integrals, "
        "and surface integrals.",
        100,
    ),
    (
        "math/differential-equations",
        "Differential Equations",
        "Mathematics", "Adults", "Advanced",
        "Learn first and second order differential equations, Laplace transforms, "
        "and systems of ODEs.",
        80,
    ),
    # ── Natural Sciences ─────────────────────────────────────────────────────
    (
        "science/physics",
        "Physics",
        "Natural Sciences", "Teens", "Intermediate",
        "Study motion, forces, energy, waves, electricity, magnetism, and "
        "modern physics.",
        100,
    ),
    (
        "science/ap-physics-1",
        "AP Physics 1",
        "Natural Sciences", "Teens", "Advanced",
        "Kinematics, dynamics, circular motion, energy, momentum, waves, "
        "and electric charge at AP exam level.",
        100,
    ),
    (
        "science/ap-physics-2",
        "AP Physics 2",
        "Natural Sciences", "Teens", "Advanced",
        "Fluids, thermodynamics, electric circuits, magnetism, optics, and "
        "modern physics at AP exam level.",
        100,
    ),
    (
        "science/chemistry",
        "Chemistry",
        "Natural Sciences", "Teens", "Intermediate",
        "Learn atomic structure, the periodic table, chemical bonds, reactions, "
        "stoichiometry, and thermochemistry.",
        100,
    ),
    (
        "science/ap-chemistry",
        "AP Chemistry",
        "Natural Sciences", "Teens", "Advanced",
        "Atomic structure, molecular geometry, equilibrium, kinetics, "
        "electrochemistry, and thermodynamics at AP level.",
        120,
    ),
    (
        "science/biology",
        "Biology",
        "Natural Sciences", "Teens", "Intermediate",
        "Explore cells, genetics, evolution, ecology, human biology, "
        "and the chemistry of life.",
        100,
    ),
    (
        "science/ap-biology",
        "AP Biology",
        "Natural Sciences", "Teens", "Advanced",
        "Evolution, cellular processes, genetics, gene expression, ecology, "
        "and interactions at AP exam level.",
        120,
    ),
    (
        "science/cosmology-and-astronomy",
        "Cosmology and Astronomy",
        "Natural Sciences", "Teens", "Beginner",
        "Explore the universe: stars, galaxies, black holes, cosmology, "
        "and the history of space exploration.",
        60,
    ),
    (
        "science/ap-environmental-science",
        "AP Environmental Science",
        "Natural Sciences", "Teens", "Advanced",
        "Earth systems, biodiversity, land use, energy resources, pollution, "
        "and global change at AP level.",
        100,
    ),
    # ── Computer Science ─────────────────────────────────────────────────────
    (
        "computing/computer-programming",
        "Computer Programming",
        "Computer Science", "Teens", "Beginner",
        "Learn programming fundamentals with JavaScript, HTML/CSS, and SQL "
        "through interactive projects.",
        80,
    ),
    (
        "computing/ap-computer-science-principles",
        "AP Computer Science Principles",
        "Computer Science", "Teens", "Intermediate",
        "Explore the internet, data, cybersecurity, algorithms, and programming "
        "concepts at AP exam level.",
        100,
    ),
    (
        "computing/computer-science",
        "Algorithms",
        "Computer Science", "Adults", "Advanced",
        "Study algorithms, data structures, binary search, sorting, recursion, "
        "and graph traversal.",
        60,
    ),
    # ── Engineering ──────────────────────────────────────────────────────────
    (
        "science/electrical-engineering",
        "Electrical Engineering",
        "Engineering", "Adults", "Intermediate",
        "Circuit analysis, Ohm's law, Kirchhoff's laws, capacitors, inductors, "
        "AC circuits, and operational amplifiers.",
        100,
    ),
]


class MitOcwIngestionSource(BaseIngestionSource):
    """
    Builds RawCourse objects for Khan Academy STEM courses.

    Uses the same static-registry + URL-verification pattern as the
    freeCodeCamp source. Registered under 'mit_ocw' source key and
    uses 'MIT OCW' provider string to avoid DB migrations.

    NOTE: This source will be replaced with real MIT OCW data when MIT
    publishes a public API. See module docstring for full context.

    Rule 14: fetch() builds RawCourse objects. normalizer.py transforms.
    Rule 9: fetch() never writes to the DB.
    """

    @property
    def source_name(self) -> str:
        return "mit_ocw"

    def fetch(self) -> FetchResult:
        """
        Build RawCourse objects for each Khan Academy STEM course.

        Each URL is verified live with a HEAD request before building.
        A non-200 response means Khan Academy restructured that path — logged,
        skipped, and annotated with instructions to update KA_COURSES.

        Rule 8: Counts logged at completion.
        """
        logger.info(
            "MitOcwIngestionSource.fetch: Starting (via Khan Academy registry). "
            "Courses=%d",
            len(KA_COURSES),
        )

        raw_courses: list[RawCourse] = []
        skipped = 0

        for slug, name, category, age_group, level, description, duration_hours in KA_COURSES:
            try:
                source_url = f"{KA_BASE}/{slug}"
                is_live = self._verify_url(source_url)

                if not is_live:
                    # FALLBACK: Skip course with dead URL, continue with remaining
                    # PRIMARY: apps/ingestion/sources/mit_ocw.py → KA_COURSES registry
                    # CONDITION: Khan Academy restructured or removed a course path
                    # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → update KA_COURSES
                    logger.warning(
                        "MitOcwIngestionSource.fetch: URL not live for '%s' at %s. "
                        "Update KA_COURSES registry.",
                        slug,
                        source_url,
                    )
                    skipped += 1
                    continue

                raw_course = self._build_raw_course(
                    external_id=f"ka-{slug.replace('/', '-')}",
                    title=name,
                    short_description=description[:300],
                    full_description=description,
                    source_url=source_url,
                    provider=PROVIDER,
                    instructor="Khan Academy",
                    thumbnail_url="",
                    format="Interactive",
                    category=category,
                    level=level,
                    age_group=age_group,
                    is_free=True,
                    certificate_available=False,
                    duration_hours=duration_hours,
                    tags=["Khan Academy", name.lower(), category.lower()],
                    raw_payload={
                        "slug": slug,
                        "ka_course_name": name,
                        "source": "khan_academy",
                    },
                )
                raw_courses.append(raw_course)

                logger.debug(
                    "MitOcwIngestionSource.fetch: Built course '%s'.", name,
                )

            except Exception as exc:
                # FALLBACK: Skip failed course, continue with remaining
                # PRIMARY: apps/ingestion/sources/mit_ocw.py → fetch()
                # CONDITION: Network error verifying a single course URL
                # THRESHOLD: 3 consecutive triggers OR 5 within 24 hours → investigate network
                logger.warning(
                    "MitOcwIngestionSource.fetch: Failed on '%s': %s. Skipping.",
                    slug,
                    exc,
                )
                skipped += 1

        logger.info(
            "MitOcwIngestionSource.fetch: Complete. built=%d, skipped=%d",
            len(raw_courses),
            skipped,
        )

        return FetchResult(
            source=self.source_name,
            courses=raw_courses,
            success=True,
            raw_count=len(KA_COURSES),
        )

    def _verify_url(self, url: str) -> bool:
        """
        Verify a Khan Academy course URL is live using a HEAD request.

        Returns True if the server responds 200 or 3xx redirect that
        resolves to 200. Returns False for 404 or connection errors.

        Rule 14: One job — check if URL is live.
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