"""Model that records a user's close-friend relationships."""

import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q, F

class CloseFriend(models.Model):
    """Link a user to a close-friend relationship."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="close_friend_owner",
    )
    friend = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="close_friend_friend",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Constraints and table name for CloseFriend."""
        db_table = "close_friend"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "friend"], name="uniq_close_friend_owner_friend"
            ),
            models.CheckConstraint(
                check=~Q(owner=F("friend")), name="chk_close_friend_not_self"
            ),
        ]

    def __str__(self):
        """Readable identifier for a close-friend link."""
        return f"CloseFriend(owner={self.owner_id}, friend={self.friend_id})"
