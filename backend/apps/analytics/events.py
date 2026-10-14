"""
Analytics event registry.

Single source of truth for all event names fired on the platform.

Rule 7 (event ownership):
- Every event has exactly one authoritative emitter
- OWNER indicates which system fires it (backend or frontend)
- FIRED FROM indicates the exact file and function/component

Rule 1 (single source of truth):
- All event name strings are defined here as constants
- No event name string is hardcoded anywhere else in the codebase
- Import from this module everywhere an event name is needed

Usage (backend):
    from apps.analytics.events import USER_SIGNED_UP
    AnalyticsService.fire_event(USER_SIGNED_UP, user_id=str(user.pk), properties={...})

Usage (frontend — frontend reads the string value, not this file):
    Frontend event names must match the string values defined here exactly.
    Any frontend event constant change must be reflected here and vice versa.

Naming convention (from Master Reference §9):
    ENTITY_ACTION   e.g. USER_SIGNED_UP, COURSE_COMPLETED
"""


# ─── User Lifecycle ───────────────────────────────────────────────────────────

USER_SIGNED_UP = "user_signed_up"
# OWNER: backend
# FIRED FROM: apps/users/views.py → RegisterView.post()
#             apps/users/google_auth.py → GoogleAuthView.post() (new users only)

USER_LOGGED_IN = "user_logged_in"
# OWNER: backend
# FIRED FROM: apps/users/views.py → LoginView.post()
#             apps/users/google_auth.py → GoogleAuthView.post() (existing users only)

USER_PROFILE_UPDATED = "user_profile_updated"
# OWNER: backend
# FIRED FROM: apps/users/views.py → MeView.patch()


# ─── Course Interaction ───────────────────────────────────────────────────────

COURSE_VIEWED = "course_viewed"
# OWNER: frontend
# FIRED FROM: frontend/src/components/courses/CourseCard.tsx
# NOTE: Backend does not fire this event. Deduplication is not required
#       because frontend is the sole emitter.

COURSE_STARTED = "course_started"
# OWNER: backend
# FIRED FROM: apps/courses/views.py → CourseStartView.post()

COURSE_COMPLETED = "course_completed"
# OWNER: backend
# FIRED FROM: apps/progress/views.py → MarkCourseCompleteView.post()


# ─── Combo Interaction ────────────────────────────────────────────────────────

COMBO_VIEWED = "combo_viewed"
# OWNER: frontend
# FIRED FROM: frontend/src/components/combos/ComboCard.tsx
# NOTE: Backend does not fire this event.

COMBO_STARTED = "combo_started"
# OWNER: backend
# FIRED FROM: apps/combos/views.py → ComboStartView.post()

COMBO_PROGRESS_UPDATED = "combo_progress_updated"
# OWNER: backend
# FIRED FROM: apps/progress/views.py → MarkCourseCompleteView.post()
# NOTE: Fired alongside COURSE_COMPLETED when the completed course is part of a combo.

COMBO_COMPLETED = "combo_completed"
# OWNER: backend
# FIRED FROM: apps/progress/views.py → MarkCourseCompleteView.post()
# NOTE: Fired only when the last required course in a combo is completed.

COMBO_CREATED = "combo_created"
# OWNER: backend
# FIRED FROM: apps/combos/views.py → ComboCreateView.post()


# ─── Search & Discovery ───────────────────────────────────────────────────────

SEARCH_PERFORMED = "search_performed"
# OWNER: frontend
# FIRED FROM: frontend/src/app/search/page.tsx

FILTER_APPLIED = "filter_applied"
# OWNER: frontend
# FIRED FROM: frontend/src/components/courses/CourseFilters.tsx


# ─── AI Interaction (Phase 2 — defined now for string consistency) ────────────

AI_QUERY_SUBMITTED = "ai_query_submitted"
# OWNER: backend
# FIRED FROM: apps/ai/views.py → AiQueryView.post()  [Phase 2 — not yet built]
# STATUS: Defined here now so the string is consistent when Phase 2 is implemented.

AI_COMBO_RECOMMENDED = "ai_combo_recommended"
# OWNER: backend
# FIRED FROM: apps/ai/services.py → AiRecommendationService.recommend()  [Phase 2]
# STATUS: Defined here now for string consistency.

AI_RESPONSE_RATED = "ai_response_rated"
# OWNER: backend
# FIRED FROM: apps/ai/views.py → AiRatingView.post()  [Phase 2]
# STATUS: Defined here now for string consistency.


# ─── Registry (for validation and replay tooling) ─────────────────────────────

# Complete list of all backend-owned events.
# Used by analytics/services.py to validate that only known events are fired.
# Frontend-owned events are NOT in this list — the backend never fires them.

BACKEND_EVENTS = frozenset({
    USER_SIGNED_UP,
    USER_LOGGED_IN,
    USER_PROFILE_UPDATED,
    COURSE_STARTED,
    COURSE_COMPLETED,
    COMBO_STARTED,
    COMBO_PROGRESS_UPDATED,
    COMBO_COMPLETED,
    COMBO_CREATED,
    AI_QUERY_SUBMITTED,
    AI_COMBO_RECOMMENDED,
    AI_RESPONSE_RATED,
})

# All events (backend + frontend) — for EventLog validation on replay.
ALL_EVENTS = frozenset({
    USER_SIGNED_UP,
    USER_LOGGED_IN,
    USER_PROFILE_UPDATED,
    COURSE_VIEWED,
    COURSE_STARTED,
    COURSE_COMPLETED,
    COMBO_VIEWED,
    COMBO_STARTED,
    COMBO_PROGRESS_UPDATED,
    COMBO_COMPLETED,
    COMBO_CREATED,
    SEARCH_PERFORMED,
    FILTER_APPLIED,
    AI_QUERY_SUBMITTED,
    AI_COMBO_RECOMMENDED,
    AI_RESPONSE_RATED,
})