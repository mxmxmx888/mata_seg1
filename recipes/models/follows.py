"""Legacy follow relationship table without reverse accessors."""

from __future__ import annotations
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q, F


def _uuid7_or_4() -> uuid.UUID:
    """Return uuid7 when available, else uuid4 (for primary keys)."""
    return getattr(uuid, "uuid7", uuid.uuid4)()

class Follows(models.Model):
    """Legacy follows relationship between two users."""
    id = models.UUIDField(primary_key=True, default=_uuid7_or_4, editable=False)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",              # no reverse accessor to avoid clashes
        db_column="author_id",
    )
    followee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",              # no reverse accessor to avoid clashes
        db_column="followee_id",
    )

    class Meta:
        """Constraints and indexes for legacy follows table."""
        db_table = "follows"
        constraints = [
            models.UniqueConstraint(fields=["author", "followee"], name="uniq_follows_author_followee"),
            models.CheckConstraint(check=~Q(author=F("followee")), name="chk_follows_not_self"),
        ]
        indexes = [
            models.Index(fields=["author"]),
            models.Index(fields=["followee"]),
        ]

    def __str__(self) -> str:
        """Readable representation for admin/debugging."""
        return f"Follows(author={self.author_id}, followee={self.followee_id})"
