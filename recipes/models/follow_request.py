"""Model capturing follow requests for private accounts."""

import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q, F

class FollowRequest(models.Model):
    """Represents a pending follow request between two users."""
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"

    STATUSES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follow_requests_sent",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follow_requests_received",
    )
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Constraints for unique, non-self follow requests."""
        db_table = "follow_request"
        constraints = [
            models.UniqueConstraint(
                fields=["requester", "target"],
                name="uniq_follow_request_requester_target",
            ),
            models.CheckConstraint(
                check=~Q(requester=F("target")),
                name="chk_follow_request_not_self",
            ),
        ]

    def __str__(self) -> str:
        """Readable summary of the follow request and status."""
        return f"FollowRequest({self.requester_id} -> {self.target_id}, {self.status})"
