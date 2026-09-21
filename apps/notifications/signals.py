# Intentionally empty.
#
# Rule 12 requires this file to exist on every app, even when unused.
#
# This app has no models of its own, so it has no post_save/pre_delete
# signals to receive. The welcome-email trigger is a signal on the User
# model, which lives in apps/users/signals.py (on_user_created) — that is
# the correct owner, since Django signals are registered on the sender's
# app. It calls send_welcome_email_task.delay(), defined in
# notifications/tasks.py.
