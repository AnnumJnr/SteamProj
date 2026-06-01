"""
Users app configuration.

Imports signals in ready() so they register with Django's signal dispatcher
on application startup. Without this, the post_save handler in signals.py
would never fire.

Rule 6: Signals are restricted to dispatching only — enforced in signals.py.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = "Users"

    def ready(self) -> None:
        """
        Import signals module to register all signal handlers.
        Called once when Django finishes its startup sequence.

        IMPORTANT: Do not perform any DB queries or model access here.
        ready() is called before migrations have run in some management
        commands — keeping it to a pure import is the only safe pattern.
        """
        import apps.users.signals  # noqa: F401