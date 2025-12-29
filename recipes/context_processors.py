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

def _fetch_notifications(user):
  return (
    Notification.objects.filter(recipient=user)
    .exclude(notification_type="follow_request", follow_request__status__in=["accepted", "rejected"])
    .select_related("sender", "post", "follow_request")
    .prefetch_related("post__images")
    .order_by("-created_at", "-id")
  )

def _pending_follow_request_sender_ids(user):
  return set(
    Notification.objects.filter(
      recipient=user,
      notification_type="follow_request",
      follow_request__status="pending",
    ).values_list("sender_id", flat=True)
  )

def _filter_notifications(notifs, pending_request_ids):
  seen_follow_senders = set()
  filtered = []
  for notif in notifs:
    if notif.notification_type != "follow":
      filtered.append(notif)
      continue
    if notif.sender_id in pending_request_ids:
      continue
    if notif.sender_id in seen_follow_senders:
      continue
    seen_follow_senders.add(notif.sender_id)
    filtered.append(notif)
  return filtered

def notifications(request):
  """Provide notifications list/count and following IDs to templates."""
  user = getattr(request, "user", None)
  if not user or not user.is_authenticated:
    return {}

  pending_request_ids = _pending_follow_request_sender_ids(user)
  notifs = list(_fetch_notifications(user))
  filtered = _filter_notifications(notifs, pending_request_ids)

  return {
    "notifications": filtered[:50],
    "unread_notifications_count": sum(1 for n in filtered if not n.is_read),
    "following_ids": set(
      Follower.objects.filter(follower=user).values_list("author_id", flat=True)
    ),
  }
