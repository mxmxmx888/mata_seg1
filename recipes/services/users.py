"""Service helpers for user lookups."""

from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

User = get_user_model()


class UserService:
    """Encapsulate common user lookups."""

    def fetch_by_username(self, username):
        """Fetch a user by username or raise 404."""
        return get_object_or_404(User, username=username)

    def first_by_email(self, email):
        """Return first user with matching email or None."""
        return User.objects.filter(email=email).first()
