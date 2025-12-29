"""Management command to seed heavy follow/following lists for testing scroll UI."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recipes.models import User, Follower


class Command(BaseCommand):
    """Add followers/following for a user to exercise infinite scroll UIs."""

    help = "Create many followers/following edges for a user to exercise modal infinite scroll."
    DEFAULT_PASSWORD = "Password123"

    def add_arguments(self, parser):
        """Define CLI arguments for the command."""
        parser.add_argument(
            "--username",
            required=True,
            help="Target username to attach followers/following to",
        )
        parser.add_argument(
            "--followers",
            type=int,
            default=150,
            help="How many followers to create",
        )
        parser.add_argument(
            "--following",
            type=int,
            default=150,
            help="How many followees the user should follow",
        )
        parser.add_argument(
            "--prefix",
            default="scrollseed",
            help="Username prefix for generated users",
        )

    def handle(self, *args, **options):
        """Create fake users and follow edges for the requested account."""
        username = options["username"]
        follower_count = max(0, options["followers"])
        following_count = max(0, options["following"])
        prefix = options["prefix"]

        target = self._get_target(username)
        follower_edges, following_edges, created_users = self._build_edges(prefix, target, follower_count, following_count)

        with transaction.atomic():
            Follower.objects.bulk_create(follower_edges, ignore_conflicts=True, batch_size=1000)
            Follower.objects.bulk_create(following_edges, ignore_conflicts=True, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(
                f"Added {len(follower_edges)} followers and {len(following_edges)} following edges for {username}. "
                f"Created {len(created_users)} new users (prefix '{prefix}')."
            )
        )

    def _get_target(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"User '{username}' not found") from exc

    def _build_edges(self, prefix, target, follower_count, following_count):
        created_users = []
        follower_edges = [
            Follower(follower=self._ensure_user(prefix, "follower", i, created_users), author=target)
            for i in range(follower_count)
        ]
        following_edges = [
            Follower(follower=target, author=self._ensure_user(prefix, "followee", i, created_users))
            for i in range(following_count)
        ]
        return follower_edges, following_edges, created_users

    def _ensure_user(self, prefix: str, suffix: str, idx: int, created_users):
        uname = f"{prefix}_{suffix}_{idx}"
        user, created = User.objects.get_or_create(
            username=uname,
            defaults={"email": f"{uname}@example.org"},
        )
        if created:
            user.set_password(self.DEFAULT_PASSWORD)
            user.save(update_fields=["password"])
            created_users.append(uname)
        return user
