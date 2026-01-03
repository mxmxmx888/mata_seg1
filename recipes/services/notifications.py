"""Service helpers for fetching and filtering notifications."""

from recipes.models import Notification, Follower


class NotificationService:
    """Encapsulate notification querying and filtering logic."""

    def __init__(self, notification_model=Notification, follower_model=Follower):
        self.notification_model = notification_model
        self.follower_model = follower_model

    def pending_request_sender_ids(self, user):
        """Return sender IDs with pending follow requests to the user."""
        return set(
            self.notification_model.objects.filter(
                recipient=user,
                notification_type="follow_request",
                follow_request__status="pending",
            ).values_list("sender_id", flat=True)
        )

    def fetch(self, user):
        """Fetch raw notifications for a user excluding resolved follow requests."""
        return (
            self.notification_model.objects.filter(recipient=user)
            .exclude(notification_type="follow_request", follow_request__status__in=["accepted", "rejected"])
            .select_related("sender", "post", "follow_request")
            .prefetch_related("post__images")
            .order_by("-created_at", "-id")
        )

    def filter_notifications(self, notifs, pending_request_ids):
        """Filter follow notifications to avoid duplicates and pending overlaps."""
        seen_follow_senders = set()
        filtered = []
        for notif in notifs:
            if notif.notification_type != "follow":
                filtered.append(notif)
                continue
            if self._should_skip_follow(notif, pending_request_ids, seen_follow_senders):
                continue
            seen_follow_senders.add(notif.sender_id)
            filtered.append(notif)
        return filtered

    def _should_skip_follow(self, notif, pending_request_ids, seen_follow_senders):
        if notif.sender_id in pending_request_ids:
            return True
        return notif.sender_id in seen_follow_senders

    def visible_notifications(self, user):
        """Return filtered notifications for a user."""
        pending_ids = self.pending_request_sender_ids(user)
        return self.filter_notifications(list(self.fetch(user)), pending_ids)

    def following_ids(self, user):
        """Return author IDs the user follows."""
        return set(
            self.follower_model.objects.filter(follower=user).values_list("author_id", flat=True)
        )

    def mark_all_read(self, user):
        """Mark all unread notifications for the user as read."""
        self.notification_model.objects.filter(recipient=user, is_read=False).update(is_read=True)
