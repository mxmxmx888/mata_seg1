"""Management command to seed the database with sample users, posts, and related data."""

import shutil
from pathlib import Path
from random import sample, randint, choice
from typing import List

from faker import Faker
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from recipes.models import User
from recipes.models.followers import Follower
from recipes.models.follows import Follows
from recipes.models.comment import Comment
from recipes.models.like import Like
from .seed_data import (
    SHOP_INGREDIENT_SETS,
    bio_phrases,
    comment_phrases,
    favourite_names,
    recipe_image_file_pool,
    user_fixtures,
)
from .seed_utils import SeedHelpers, create_username, create_email
from recipes.models.recipe_post import RecipePost, RecipeImage
from recipes.models.recipe_step import RecipeStep
from recipes.models.favourite import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.models.ingredient import Ingredient

class Command(SeedHelpers, BaseCommand):
    """Management command to seed the database with sample users/posts/data."""
    USER_COUNT = 200
    DEFAULT_PASSWORD = 'Password123'
    help = 'Seeds the database with sample data'

    def add_arguments(self, parser):
        """Add optional flags for safe seeding."""
        parser.add_argument(
            "--reset-media",
            action="store_true",
            help="Delete media/recipes, media/shop_items, and media/avatars before seeding (dev safeguard).",
        )

    def __init__(self, *args, **kwargs):
        """Set up faker instance for generating seed content."""
        super().__init__(*args, **kwargs)
        self.faker = Faker('en_GB')

    def handle(self, *args, **options):
        """Run the full seeding sequence."""
        if options.get("reset_media"):
            self.reset_media_dirs()
        self.create_users()
        self.seed_followers_and_follows(follow_k=5)
        self.seed_recipe_posts(per_user=2)
        self.seed_recipe_steps(min_steps=4, max_steps=7)
        self.seed_favourites(per_user=2)
        self.seed_ingredients()
        self.seed_likes(max_likes_per_post=20)
        self.seed_comments(max_comments_per_post=5)
        self.stdout.write(self.style.SUCCESS("Seeding complete"))

    def create_users(self):
        """Generate fixture and random users."""
        self.generate_user_fixtures()
        self.generate_random_users()

    def generate_user_fixtures(self):
        """Create users from predefined fixture data."""
        for data in user_fixtures:
            self.try_create_user(data)

    def generate_random_users(self):
        """Create random users until USER_COUNT is reached."""
        user_count = User.objects.count()
        while  user_count < self.USER_COUNT:
            print(f"Seeding user {user_count}/{self.USER_COUNT}", end='\r')
            self.generate_user()
            user_count = User.objects.count()
        print("User seeding complete.      ")

    def generate_user(self):
        """Create a single random user."""
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        email = create_email(first_name, last_name)
        username = create_username(first_name, last_name)
        self.try_create_user({'username': username, 'email': email, 'first_name': first_name, 'last_name': last_name})
       
    def try_create_user(self, data):
        """Try to create a user and ignore duplicates/errors."""
        try:
            self.create_user(data)
        except:
            pass

    def seed_followers_and_follows(self, follow_k: int = 5) -> None:
        """Create follower/followee edges for sample users."""
        ids = list(User.objects.values_list("id", flat=True))
        n = len(ids)
        if n < 2:
            return

        k = max(0, min(follow_k, n - 1))
        edges: set[tuple[str, str]] = set()

        for author in ids:
            pool = [x for x in ids if x != author]
            followees = sample(pool, k) if k else []
            for f in followees:
                edges.add((author, f))

        follower_rows = [Follower(follower_id=a, author_id=b) for (a, b) in edges]
        follows_rows = [Follows(author_id=a, followee_id=b) for (a, b) in edges]

        with transaction.atomic():
            Follower.objects.bulk_create(follower_rows, ignore_conflicts=True, batch_size=1000)
            Follows.objects.bulk_create(follows_rows, ignore_conflicts=True, batch_size=1000)

    def seed_recipe_posts(self, *, per_user: int = 3) -> None:
        """Generate recipe posts and images for all users."""
        user_ids = list(User.objects.values_list("id", flat=True))
        if not user_ids:
            return

        posts_to_create: List[RecipePost] = []
        images_to_create: List[RecipeImage] = []
        for author_id in user_ids:
            new_posts, new_images = self._build_posts_for_author(author_id, per_user, recipe_image_file_pool)
            posts_to_create.extend(new_posts)
            images_to_create.extend(new_images)

        with transaction.atomic():
            RecipePost.objects.bulk_create(posts_to_create, ignore_conflicts=True, batch_size=500)
            RecipeImage.objects.bulk_create(images_to_create, ignore_conflicts=True, batch_size=500)

        self.stdout.write(
            f"Recipe posts created: {len(posts_to_create)}; images attempted: {len(images_to_create)}"
        )

    def seed_recipe_steps(self, *, min_steps: int = 4, max_steps: int = 7) -> None:
        """Attach random steps to each recipe post."""
        post_ids = list(RecipePost.objects.values_list("id", flat=True))
        if not post_ids:
            return

        rows: List[RecipeStep] = []

        for post_id in post_ids:
            step_count = randint(min_steps, max_steps)
            for pos in range(1, step_count + 1):
                text = self.faker.sentence(nb_words=12)
                rows.append(
                    RecipeStep(
                        recipe_post_id=post_id,
                        position=pos,
                        description=text[:1000],
                    )
                )

        with transaction.atomic():
            RecipeStep.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)

        self.stdout.write(f"recipe steps created (attempted): {len(rows)}")

    def seed_likes(self, max_likes_per_post: int = 20) -> None:
        """Create random likes for posts up to a max per post."""
        users = list(User.objects.values_list("id", flat=True))
        posts = list(RecipePost.objects.values_list("id", flat=True))

        if not users or not posts:
            return

        rows = _build_like_rows(users, posts, max_likes_per_post)

        with transaction.atomic():
            Like.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)

        self.stdout.write(f"likes created: {len(rows)}")

    def seed_comments(self, max_comments_per_post: int = 5) -> None:
        """Generate random comments for each post."""
        users = list(User.objects.values_list("id", flat=True))
        posts = list(RecipePost.objects.values_list("id", flat=True))

        if not users or not posts:
            return

        rows = []

        for post_id in posts:
            comment_count = randint(0, max_comments_per_post)

            commenters = sample(users, min(len(users), comment_count))
            for user_id in commenters:
                rows.append(
                    Comment(
                        recipe_post_id=post_id,
                        user_id=user_id,
                        text=choice(comment_phrases),
                    )
                )

        Comment.objects.bulk_create(rows, ignore_conflicts=True, batch_size=500)
        self.stdout.write(f"Comments created: {len(rows)}")

    def seed_ingredients(self) -> None:
        """Attach example ingredients to each recipe post."""
        post_ids = list(RecipePost.objects.values_list("id", flat=True))
        if not post_ids:
            return

        if not SHOP_INGREDIENT_SETS:
            self.stdout.write("no shop ingredient sets configured, skipping ingredients seeding.")
            return

        rows: List[Ingredient] = []
        set_count = len(SHOP_INGREDIENT_SETS)
        for idx, post_id in enumerate(post_ids):
            ingredient_set = SHOP_INGREDIENT_SETS[idx % set_count]
            rows.extend(self._build_ingredients_for_post(post_id, ingredient_set))

        with transaction.atomic():
            Ingredient.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)

        self.stdout.write(f"ingredients created (attempted): {len(rows)}")

    def seed_favourites(self, *, per_user: int = 2) -> None:
        """Create favourites and saved items for users."""
        user_ids = list(User.objects.values_list("id", flat=True))
        if not user_ids:
            return

        posts = self._get_recipe_posts_for_favourites()
        if not posts:
            return

        favourites_to_create = self._build_favourites(user_ids, per_user, favourite_names)
        self._bulk_create_favourites(favourites_to_create)
        favs_by_user = self._fetch_favourites_by_user(user_ids)
        items_to_create = self._build_favourite_items(user_ids, posts, favs_by_user)
        self._bulk_create_favourite_items(items_to_create)
        self.stdout.write(
            f"favourites seeded: {len(favourites_to_create)} collections, {len(items_to_create)} items attempted"
        )

    def _get_recipe_posts_for_favourites(self) -> List[str]:
        """Fetch IDs for all recipe posts to seed favourites against."""
        posts = list(RecipePost.objects.values_list("id", flat=True))
        if not posts:
            self.stdout.write("no recipe posts found, skipping favourites seeding.")
        return posts

    def _bulk_create_favourites(self, favourites: List[Favourite]) -> None:
        """Bulk create Favourite rows with conflict tolerance."""
        with transaction.atomic():
            Favourite.objects.bulk_create(
                favourites,
                ignore_conflicts=True,
                batch_size=500
            )

    def _bulk_create_favourite_items(self, items: List[FavouriteItem]) -> None:
        """Bulk create FavouriteItem rows with conflict tolerance."""
        with transaction.atomic():
            FavouriteItem.objects.bulk_create(
                items,
                ignore_conflicts=True,
                batch_size=1000
            )

    def reset_media_dirs(self) -> None:
        """Safely clear recipe/shop media folders before seeding."""
        media_root = Path(settings.MEDIA_ROOT)
        targets = [
            media_root / "recipes",
            media_root / "shop_items",
            media_root / "avatars",
        ]
        for path in targets:
            _ensure_dir(path)
            _clear_children(path)
        self.stdout.write(self.style.WARNING("Media directories reset (recipes, shop_items, avatars)."))

    def create_user(self, data):
        """Helper to create a user with default password."""
        User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=Command.DEFAULT_PASSWORD,
            first_name=data['first_name'],
            last_name=data['last_name'],
            bio = choice(bio_phrases)
        )

def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def _clear_children(path: Path):
    for child in path.iterdir():
        _remove_child(child)

def _remove_child(child: Path):
    if child.is_dir():
        shutil.rmtree(child, ignore_errors=True)
        return
    try:
        child.unlink()
    except FileNotFoundError:
        pass

def _build_like_rows(users, posts, max_likes_per_post):
    rows = []
    for post_id in posts:
        like_count = randint(0, min(max_likes_per_post, len(users)))
        for user_id in sample(users, like_count):
            rows.append(Like(user_id=user_id, recipe_post_id=post_id))
    return rows
