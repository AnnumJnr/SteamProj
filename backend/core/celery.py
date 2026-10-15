"""
Celery application configuration.
This module is imported by core/__init__.py to ensure Celery is
initialized when Django starts.
"""

import os

from celery import Celery

# Point Celery at the correct Django settings module.
# Falls back to development settings locally.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")

app = Celery("stem_platform")

# Read Celery config from Django settings, using the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps.
# Celery will look for a tasks.py file in each app.
app.autodiscover_tasks()