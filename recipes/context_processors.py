from __future__ import annotations

from typing import Dict

from django.http import HttpRequest

from recipes.forms import UserForm, PasswordForm
from recipes.models import Notification


def edit_profile_form(request: HttpRequest) -> Dict[str, object]:
  """
  Provide a UserForm instance for the logged-in user.

  This is used to render the global “Edit profile” settings modal
  from anywhere that includes the app navbar.
  """
  user = getattr(request, "user", None)
  if not user or not user.is_authenticated:
    return {}
  return {
    "edit_profile_form": UserForm(instance=user),
    "password_form": PasswordForm(user=user),
  }

def notifications(request):
    if request.user.is_authenticated:
        notifs = Notification.objects.filter(recipient=request.user).select_related('sender', 'post')[:10]
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {
            'notifications': notifs,
            'unread_notifications_count': unread_count
        }
    return {}
