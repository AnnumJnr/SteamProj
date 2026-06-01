"""
Abstract base models.
All concrete models across the platform should inherit from TimestampedModel
to get consistent UUID primary keys and automatic timestamp tracking.
"""

import uuid

from django.db import models


class TimestampedModel(models.Model):
    """
    Abstract base model providing:
    - UUID primary key (avoids sequential ID exposure)
    - created_at / updated_at auto-timestamps

    All platform models inherit from this.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Universally unique identifier. Auto-generated on creation.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was first created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp of the most recent update to this record.",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]