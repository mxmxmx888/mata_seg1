from __future__ import annotations
from typing import Dict
from django.http import HttpRequest
from recipes.forms import UserForm, PasswordForm
from recipes.models import Notification, Follower
from recipes.services import ProfileDisplayService

def edit_profile_form(request: HttpRequest) -> Dict[str, object]:
  """Inject profile edit and password forms plus avatar URLs into templates."""
  user = getattr(request, "user", None)
  if not user or not user.is_authenticated:
    return {}
  display = ProfileDisplayService(user)
  return {
    "edit_profile_form": UserForm(instance=user),
    "password_form": PasswordForm(user=user),
    "edit_profile_avatar_url": display.editing_avatar_url(),
    "navbar_avatar_url": display.navbar_avatar_url(),
  }

def notifications(request):
    """Provide notifications list/count and following IDs to templates."""
    if request.user.is_authenticated:
        notifs_qs = Notification.objects.filter(recipient=request.user).exclude(
            notification_type="follow_request",
            follow_request__status__in=["accepted", "rejected"],
        ).select_related("sender", "post", "follow_request").prefetch_related("post__images").order_by("-created_at")
        notifs = list(notifs_qs)
        following_ids = set(
            Follower.objects.filter(follower=request.user).values_list("author_id", flat=True)
        )
        pending_request_ids = set(
            Notification.objects.filter(
                recipient=request.user,
                notification_type="follow_request",
                follow_request__status="pending",
            ).values_list("sender_id", flat=True)
        )
        seen_follow_senders = set()
        filtered = []
        for n in notifs:
            if n.notification_type == "follow" and n.sender_id in pending_request_ids:
                continue
            if n.notification_type == "follow":
                if n.sender_id in seen_follow_senders:
                    continue
                seen_follow_senders.add(n.sender_id)
            filtered.append(n)
        notifs = filtered
        unread_count = sum(1 for n in notifs if not n.is_read)
        return {
            'notifications': notifs,
            'unread_notifications_count': unread_count,
            'following_ids': following_ids,
        }
    return {}
