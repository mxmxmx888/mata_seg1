from __future__ import annotations
from typing import Dict
from django.http import HttpRequest
from recipes.forms import UserForm, PasswordForm
from recipes.services import ProfileDisplayService
from recipes.services.notifications import NotificationService

_notification_service = NotificationService()

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
  return _notification_service.fetch(user)

def _pending_follow_request_sender_ids(user):
  return _notification_service.pending_request_sender_ids(user)

def _filter_notifications(notifs, pending_request_ids):
  return _notification_service.filter_notifications(notifs, pending_request_ids)

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
    "following_ids": _notification_service.following_ids(user),
  }
