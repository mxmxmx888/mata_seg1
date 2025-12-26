"""Model representing follower→author relationships."""

from __future__ import annotations
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q, F


def _uuid7_or_4() -> uuid.UUID:
    """Return uuid7 when available, else uuid4 (for primary keys)."""
    return getattr(uuid, "uuid7", uuid.uuid4)()

class Follower(models.Model):
    """Follower relationship where follower subscribes to author."""
    id = models.UUIDField(primary_key=True, default=_uuid7_or_4, editable=False)

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",      # user.following -> Follower rows this user created (outbound)
        db_column="follower_id",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",      # user.followers -> Follower rows pointing to this user (inbound)
        db_column="author_id",
    )

    class Meta:
        """DB metadata and constraints for follower relationships."""
        db_table = "followers"
        constraints = [
            models.UniqueConstraint(fields=["follower", "author"], name="uniq_followers_follower_author"),
            models.CheckConstraint(check=~Q(follower=F("author")), name="chk_followers_not_self"),
        ]
        indexes = [
            models.Index(fields=["follower"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self) -> str:
        """Readable representation for admin/debugging."""
        return f"Follower(follower={self.follower_id}, author={self.author_id})"
