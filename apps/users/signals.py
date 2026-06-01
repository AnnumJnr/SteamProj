"""
User signals.

Responsibilities (Rule 6 — signals dispatch tasks only):
- On User creation: dispatch the welcome email task
- On User creation: create the UserProfile with default values

This is the ONLY place UserProfile is created. The # TEMPORARY blocks
in users/services.py and users/google_auth.py have been removed.
After profile creation, Google OAuth flows update display_name and
avatar_url directly on the profile — the signal only creates with defaults.

Rule 6 enforced:
- No business logic here
- No external API calls
- No direct DB writes beyond profile creation (which is an inherent
  part of the user creation contract, not business logic)
- Task dispatch is the primary responsibility
"""

from __future__ import annotations

# TYPE_CHECKING guard: User is imported here only for Pylance/mypy type analysis.
# At runtime this block is never executed, so no circular import risk.
# get_user_model() is used at runtime (in the decorator and function body).
# Without this guard, Pylance flags `instance: User` and `user: User` as
# "Variable not allowed in type expression" (reportInvalidTypeForm) because
# get_user_model() returns a runtime value, not a static type alias.
import logging
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.tasks import send_welcome_email_task

if TYPE_CHECKING:
    from apps.users.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=get_user_model())
def on_user_created(sender, instance: User, created: bool, **kwargs) -> None:
    """
    Fires when a User record is saved.

    On creation only:
    1. Creates the UserProfile with default values.
    2. Dispatches the welcome email Celery task.

    Why profile creation lives here (not purely in a task):
    UserProfile is required immediately after user creation — serializers
    and views expect `user.profile` to exist. Creating it in a Celery task
    would introduce a race condition where the profile might not exist when
    the registration response is serialized. Creating it synchronously in
    the signal guarantees it exists before the view returns.

    The welcome email, by contrast, has no timing requirement on the
    response — it is safely deferred to a Celery task.

    Note on transaction safety:
    transaction.on_commit() ensures the task is only dispatched after the
    database transaction that created the user has fully committed. Without
    this, the Celery worker could receive the task before the User row is
    visible in the DB (a race condition on fast machines or with eager mode).
    """
    if not created:
        return

    _create_user_profile(instance)

    # Dispatch welcome email after the DB transaction commits.
    # In CELERY_TASK_ALWAYS_EAGER mode (development), on_commit callbacks
    # fire at the end of the current atomic block or immediately if no
    # transaction is active.
    transaction.on_commit(lambda: send_welcome_email_task.delay(instance.pk))
    logger.info(
        "on_user_created: Profile created and welcome email task queued for user %s",
        instance.email,
    )


def _create_user_profile(user: User) -> None:
    """
    Create a UserProfile with default values for a newly created user.

    Called synchronously within the post_save signal to guarantee the profile
    exists before the registration response is returned to the client.

    Default values:
    - display_name: ""  (user can set via profile update)
    - avatar_url: ""    (Google OAuth flow updates this after creation)
    - age_group: "Adults" (UserProfile model default)
    - bio: ""
    - interests: []

    Google OAuth note:
    When a Google user is created, this signal fires and creates the profile
    with display_name="" and avatar_url="". The Google auth flow
    (_get_or_create_google_user in google_auth.py) then immediately calls
    profile.update() with the Google display_name and avatar_url. This is
    intentional — the signal owns creation, the auth flow owns enrichment.
    """
    from apps.users.models import UserProfile  # local import to avoid circular import

    try:
        UserProfile.objects.create(user=user)
        logger.info(
            "_create_user_profile: UserProfile created for user %s",
            user.email,
        )
    except Exception:
        # If profile creation fails, log the error but do not raise.
        # The user account was already created — a missing profile is recoverable
        # via the guard in UserProfileService.update_profile().
        logger.error(
            "_create_user_profile: Failed to create UserProfile for user %s. "
            "Profile will be created on next profile access.",
            user.email,
            exc_info=True,
        )