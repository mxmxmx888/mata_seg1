"""Shared helpers for seed management commands."""

from django.core.management.base import CommandError

from recipes.models import User


def get_user_or_error(username):
    """Fetch a user by username or raise a friendly CommandError."""
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist as exc:
        raise CommandError(f"User '{username}' not found") from exc
