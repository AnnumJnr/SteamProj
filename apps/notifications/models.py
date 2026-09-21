# Intentionally empty.
#
# Rule 12 requires this file to exist on every app, even when unused.
#
# MVP scope is email-only notifications (see STEM_PLATFORM_MASTER_REFERENCE.md,
# "Email / Notifications"). There is nothing to persist — emails.py builds a
# message, services.py sends it, nothing is stored in the database.
#
# In-app notifications (which would need a Notification model here) are
# Phase 2 (Growth), not MVP. Add the model when that phase starts.
