"""Service helpers for managing follow relationships and requests."""

from django.db import transaction
from django.utils import timezone
from recipes.models import CloseFriend, Follower, Notification, FollowRequest

class FollowService:
    """Domain service to manage follow relationships and requests."""
    def __init__(self, actor):
        """Create a FollowService bound to the acting user."""
        self.actor = actor

    def _can_act(self, target):
        """Return True when the actor is authenticated and different to the target."""
        return (
            self.actor
            and getattr(self.actor, "is_authenticated", False)
            and target
            and self.actor != target
        )

    def _notify(self, recipient, sender, notif_type, follow_request=None):
        """Create a notification for a follow/follow-request event."""
        Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notif_type,
            follow_request=follow_request,
        )

    def _cleanup_request_prompt(self, target):
        """Remove pending follow-request notifications created by this actor."""
        Notification.objects.filter(
            recipient=target,
            sender=self.actor,
            notification_type="follow_request",
        ).delete()

    def is_following(self, target):
        """Return True if the actor follows the target."""
        if not self._can_act(target):
            return False
        return Follower.objects.filter(follower=self.actor, author=target).exists()

    def pending_request(self, target):
        """Return the pending follow request to the target if it exists."""
        if not self._can_act(target):
            return None
        return FollowRequest.objects.filter(
            requester=self.actor,
            target=target,
            status=FollowRequest.STATUS_PENDING,
        ).first()

    @transaction.atomic
    def follow_user(self, target):
        """Follow a target user or create a follow request if target is private."""
        if not self._can_act(target):
            return {"status": "noop"}
        if Follower.objects.filter(follower=self.actor, author=target).exists():
            return {"status": "following"}
        if not getattr(target, "is_private", False):
            return self._follow_public_target(target)
        return self._request_private_follow(target)

    def _follow_public_target(self, target):
        Follower.objects.get_or_create(follower=self.actor, author=target)
        FollowRequest.objects.filter(requester=self.actor, target=target).delete()
        self._notify(target, self.actor, "follow")
        return {"status": "following"}

    def _request_private_follow(self, target):
        fr, created = FollowRequest.objects.get_or_create(
            requester=self.actor,
            target=target,
            defaults={
                "status": FollowRequest.STATUS_PENDING,
                "created_at": timezone.now(),
            },
        )
        if not created and fr.status != FollowRequest.STATUS_PENDING:
            fr.status = FollowRequest.STATUS_PENDING
            fr.created_at = timezone.now()
            fr.save(update_fields=["status", "created_at"])
        self._notify(target, self.actor, "follow_request", follow_request=fr)
        return {"status": "requested"}

    @transaction.atomic
    def cancel_request(self, target):
        """Cancel a pending follow request for the actor."""
        if not self._can_act(target):
            return False
        FollowRequest.objects.filter(
            requester=self.actor,
            target=target,
            status=FollowRequest.STATUS_PENDING,
        ).delete()
        self._cleanup_request_prompt(target)
        return True

    @transaction.atomic
    def unfollow(self, target):
        """Unfollow a target user if currently following."""
        if not self._can_act(target):
            return False
        Follower.objects.filter(follower=self.actor, author=target).delete()
        return True

    def remove_follower(self, target):
        """Remove a follower from the actor and drop close-friend link if present."""
        if not self._can_act(target):
            return {"status": "noop"}
        Follower.objects.filter(author=self.actor, follower=target).delete()
        CloseFriend.objects.filter(owner=self.actor, friend=target).delete()
        return {"status": "removed"}

    def remove_following(self, target):
        """Alias for unfollow to mirror remove_follower semantics."""
        if not self._can_act(target):
            return {"status": "noop"}
        self.unfollow(target)
        return {"status": "removed"}

    def add_close_friend(self, target):
        """Add a target as a close friend if they already follow the actor."""
        if not self._can_act(target):
            return {"status": "noop"}
        if not Follower.objects.filter(author=self.actor, follower=target).exists():
            return {"status": "requires_follow"}
        CloseFriend.objects.get_or_create(owner=self.actor, friend=target)
        return {"status": "added"}

    def remove_close_friend(self, target):
        """Remove a target from the actor's close friends list."""
        if not self._can_act(target):
            return {"status": "noop"}
        CloseFriend.objects.filter(owner=self.actor, friend=target).delete()
        return {"status": "removed"}

    @transaction.atomic
    def toggle_follow(self, target):
        """Toggle follow/request state for a target user."""
        if not self._can_act(target):
            return {"status": "noop"}

        if Follower.objects.filter(follower=self.actor, author=target).exists():
            self.unfollow(target)
            return {"status": "unfollowed"}

        if FollowRequest.objects.filter(
            requester=self.actor,
            target=target,
            status=FollowRequest.STATUS_PENDING,
        ).exists():
            self.cancel_request(target)
            return {"status": "request_cancelled"}

        return self.follow_user(target)

    @transaction.atomic
    def accept_request(self, request_id):
        """Accept a follow request by id when the actor is the target."""
        fr = self._get_pending_request(request_id)
        if not fr:
            return False

        Follower.objects.get_or_create(follower=fr.requester, author=fr.target)
        fr.status = FollowRequest.STATUS_ACCEPTED
        fr.save(update_fields=["status"])
        self._notify(fr.requester, fr.target, "follow")
        self._retarget_request_notification(fr)
        return True

    def _get_pending_request(self, request_id):
        try:
            return FollowRequest.objects.select_for_update().get(
                id=request_id,
                target=self.actor,
                status=FollowRequest.STATUS_PENDING,
            )
        except FollowRequest.DoesNotExist:
            return None

    def _retarget_request_notification(self, follow_request):
        """Keep the original request notification visible but mark it as a follow."""
        notif = (
            Notification.objects.filter(follow_request=follow_request, recipient=self.actor)
            .order_by("-created_at", "-id")
            .first()
        )
        if not notif:
            return
        notif.notification_type = "follow"
        notif.follow_request = None
        notif.save(update_fields=["notification_type", "follow_request"])

    @transaction.atomic
    def reject_request(self, request_id):
        """Reject a follow request by id when the actor is the target."""
        try:
            fr = FollowRequest.objects.select_for_update().get(
                id=request_id,
                target=self.actor,
                status=FollowRequest.STATUS_PENDING,
            )
        except FollowRequest.DoesNotExist:
            return False
        fr.status = FollowRequest.STATUS_REJECTED
        fr.save(update_fields=["status"])
        Notification.objects.filter(follow_request=fr, recipient=self.actor).delete()
        return True
