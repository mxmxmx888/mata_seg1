"""Management command to backfill many posts on a profile for scroll testing."""

from datetime import timedelta
from random import choice, randint, sample

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from faker import Faker

from recipes.management.commands.seed_data import categories, recipe_image_file_pool, tags_pool
from recipes.management.commands.seed_utils import SeedHelpers
from recipes.models import RecipePost, User
from recipes.models.recipe_post import RecipeImage


class Command(SeedHelpers, BaseCommand):
    """Create a batch of posts for a given user to exercise profile pagination."""

    help = "Create many posts for a user's profile to exercise infinite scroll."

    def add_arguments(self, parser):
        """Define CLI arguments for post generation."""
        parser.add_argument(
            "--username",
            required=True,
            help="Target username to attach posts to",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=80,
            help="How many posts to create (defaults to 80).",
        )
        parser.add_argument(
            "--prefix",
            default="Scroll Test Post",
            help="Prefix for generated post titles.",
        )

    def handle(self, *args, **options):
        """Create the requested posts and write a summary to stdout."""
        username = options["username"]
        count = max(1, min(int(options["count"]), 500))
        prefix = options["prefix"]

        try:
            author = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"User '{username}' not found") from exc

        faker = Faker("en_GB")
        now = timezone.now()

        posts: list[RecipePost] = []
        images: list[RecipeImage] = []
        for idx in range(count):
            created_at = now - timedelta(minutes=idx)
            title = f"{prefix} {idx + 1:03d}"
            tag_count = randint(0, min(3, len(tags_pool)))
            post_tags = sample(tags_pool, k=tag_count) if tag_count else []

            post = RecipePost(
                author=author,
                title=title[:255],
                description=faker.paragraph(nb_sentences=3)[:4000],
                image=choice(recipe_image_file_pool) if recipe_image_file_pool else None,
                prep_time_min=randint(0, 30),
                cook_time_min=randint(0, 60),
                serves=choice([0, 2, 4, 6]),
                tags=post_tags,
                nutrition="",
                category=choice(categories) if categories else None,
                visibility=RecipePost.VISIBILITY_PUBLIC,
                published_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )

            posts.append(post)
            if recipe_image_file_pool:
                images.extend(self._build_recipe_images(post, recipe_image_file_pool))

        RecipePost.objects.bulk_create(posts, batch_size=500)
        if images:
            RecipeImage.objects.bulk_create(images, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(posts)} posts for {username} (prefix '{prefix}'). "
                f"Attached images: {len(images)}"
            )
        )
