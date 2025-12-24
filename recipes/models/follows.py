from __future__ import annotations
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q, F

"""
Follows model

This table also stores a “who follows who” relationship, but it’s designed as a
plain join table with NO reverse accessors on the User model.

Each row means:
    author  ->  followee

So if Alice follows Bob:
- author = Alice
- followee = Bob

Why `related_name="+"`?
- It disables the reverse relation on User entirely (no `user.follows_set` etc.).
- This is useful when you already have another follow model (like `Follower`)
  and you want to avoid reverse-name clashes or confusion.

Constraints / integrity rules:
- A user can’t follow the same person twice (UniqueConstraint on author+followee).
- A user can’t follow themselves (CheckConstraint).

Indexes:
- Indexes on author and followee speed up “who do I follow?” and
  “who follows this user?” style queries.

ID:
- Uses uuid7 if available, otherwise uuid4 (portable across Python versions).

The `__str__` method is for readable debug/admin output.
"""

def _uuid7_or_4() -> uuid.UUID:
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
        return f"Follows(author={self.author_id}, followee={self.followee_id})"
