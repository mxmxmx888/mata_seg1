from django.db import transaction
from django.utils import timezone
from recipes.models import Follower, Notification, FollowRequest

class FollowService:
    def __init__(self, actor):
        self.actor = actor

    def _can_act(self, target):
        return (
            self.actor
            and getattr(self.actor, "is_authenticated", False)
            and target
            and self.actor != target
        )

    def _notify(self, recipient, sender, notif_type, follow_request=None):
        Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notif_type,
            follow_request=follow_request,
        )

    def _cleanup_request_prompt(self, target):
        Notification.objects.filter(
            recipient=target,
            sender=self.actor,
            notification_type="follow_request",
        ).delete()

    @transaction.atomic
    def follow_user(self, target):
        if not self._can_act(target):
            return {"status": "noop"}

        # If already following, do nothing.
        if Follower.objects.filter(follower=self.actor, author=target).exists():
            return {"status": "following"}

        # Public target → immediate follow (Scenarios A, B)
        if not getattr(target, "is_private", False):
            Follower.objects.get_or_create(follower=self.actor, author=target)
            # Remove any pending request artifacts
            FollowRequest.objects.filter(
                requester=self.actor, target=target
            ).delete()
            self._notify(target, self.actor, "follow")
            return {"status": "following"}

        # Private target → request (Scenarios C, D)
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
        if not self._can_act(target):
            return False
        Follower.objects.filter(follower=self.actor, author=target).delete()
        return True

    @transaction.atomic
    def toggle_follow(self, target):
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
        try:
            fr = FollowRequest.objects.select_for_update().get(
                id=request_id,
                target=self.actor,
                status=FollowRequest.STATUS_PENDING,
            )
        except FollowRequest.DoesNotExist:
            return False

        Follower.objects.get_or_create(follower=fr.requester, author=fr.target)
        fr.status = FollowRequest.STATUS_ACCEPTED
        fr.save(update_fields=["status"])
        self._notify(fr.requester, fr.target, "follow")

        # Keep the original request notification visible, but mark it as a "follow"
        # so the UI shows "[user] started following you" instead of disappearing.
        existing_notif = (
            Notification.objects.filter(follow_request=fr, recipient=self.actor)
            .order_by("-created_at", "-id")
            .first()
        )
        if existing_notif:
            existing_notif.notification_type = "follow"
            existing_notif.follow_request = None
            existing_notif.save(update_fields=["notification_type", "follow_request"])
        return True

    @transaction.atomic
    def reject_request(self, request_id):
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
