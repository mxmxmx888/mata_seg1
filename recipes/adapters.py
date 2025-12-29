import re
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model


def _unique_username(base, user_model, exclude_user_id=None):
    """
    Normalize a base string and make it unique for the given User model.
    """
    base = (base or "").strip().lstrip("@")
    base = re.sub(r"[^a-zA-Z0-9_.]", "", base).lower() or "user"

    username = base
    counter = 1
    qs = user_model.objects.filter(username=username)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    while qs.exists():
        username = f"{base}{counter}"
        counter += 1
        qs = user_model.objects.filter(username=username)
        if exclude_user_id:
            qs = qs.exclude(pk=exclude_user_id)

    return username


class CustomAccountAdapter(DefaultAccountAdapter):
    """Customise account behaviour for username generation and redirects."""

    def clean_username(self, username, shallow=False):
        """
        Allow usernames without '@'. Only allow letters, digits, underscore, dot.
        Raise ValidationError (not ValueError) so allauth can handle it.
        """
        if username.startswith("@"):
            username = username[1:]
        if not re.match(r"^[a-zA-Z0-9_.]+$", username):
            raise ValidationError("Username must contain only letters, numbers, underscores, or dots.")
        return username

    def populate_username(self, request, user):
        """
        Deterministic username generation:
        - If user.username exists -> clean and use it.
        - Else use email local-part / first_name / 'user'
        - If collision -> append 1,2,3... (so 'test' -> 'test1')
        """
        UserModel = type(user)

        base = (user.username or "").strip()
        if base:
            base = base.lstrip("@")
        else:
            email = (getattr(user, "email", "") or "").strip()
            if email and "@" in email:
                base = email.split("@", 1)[0]
            else:
                base = (getattr(user, "first_name", "") or "").strip() or "user"

        return _unique_username(base, UserModel, exclude_user_id=user.pk or None)

    def get_login_redirect_url(self, request):
        """Send users to ?next when provided, otherwise to the dashboard."""
        return super().get_login_redirect_url(request)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Ensure social signups always get a unique username before hitting the DB.
    """

    def populate_user(self, request, sociallogin, data):
        """Populate user fields when authenticating via a third-party provider."""
        user = super().populate_user(request, sociallogin, data)

        UserModel = type(user)
        candidate = (
            getattr(user, "username", None)
            or data.get("username")
            or (data.get("email", "") or "").split("@")[0]
            or (data.get("first_name") or "")
            or (data.get("name") or "")
            or "user"
        )

        user.username = _unique_username(candidate, UserModel, exclude_user_id=user.pk or None)
        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Attempt to attach to an existing user with the same email if a uniqueness
        conflict happens during social signup.
        """
        try:
            return super().save_user(request, sociallogin, form=form)
        except IntegrityError:
            return self._connect_existing_user_or_raise(request, sociallogin)

    def _connect_existing_user_or_raise(self, request, sociallogin):
        existing_user = self._find_existing_user(sociallogin)
        if not existing_user:
            raise
        sociallogin.connect(request, existing_user)
        return existing_user

    def _find_existing_user(self, sociallogin):
        email = (getattr(sociallogin.user, "email", "") or "").strip()
        if not email:
            return None
        User = get_user_model()
        return User.objects.filter(email__iexact=email).first()
