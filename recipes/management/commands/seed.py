"""
Management command to seed the database with demo data.

This command creates a small set of named fixture users and then fills up
to ``USER_COUNT`` total users using Faker-generated data. Existing records
are left untouched—if a create fails (e.g., due to duplicates), the error
is swallowed and generation continues.
"""

import os
from typing import Any, Dict, List, Set, Tuple
from random import sample, randint, choice
from uuid import uuid4

from faker import Faker
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from recipes.models import User
from recipes.models.followers import Follower
from recipes.models.follows import Follows
from recipes.models.recipe_post import RecipePost, RecipeImage
from recipes.models.recipe_step import RecipeStep
from recipes.models.favourite import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.models.comment import Comment
from recipes.models.like import Like
from recipes.models.ingredient import Ingredient



user_fixtures = [
    {'username': '@johndoe', 'email': 'john.doe@example.org', 'first_name': 'John', 'last_name': 'Doe'},
    {'username': '@janedoe', 'email': 'jane.doe@example.org', 'first_name': 'Jane', 'last_name': 'Doe'},
    {'username': '@charlie', 'email': 'charlie.johnson@example.org', 'first_name': 'Charlie', 'last_name': 'Johnson'},
]
image_pool = [
    "/static/images/chotko.jpeg",
    "/static/images/toothless.jpg",
    "/static/images/meal.jpg.webp",



]
categories = ["Breakfast", "Lunch", "Dinner", "Dessert", "Vegan"]
tags_pool = ["quick", "family", "spicy", "budget", "comfort", "healthy", "high_protein", "low_carb"]
favourite_names = [
    "favourites",
    "dinner ideas",
    "quick meals",
    "healthy",
    "desserts",
    "meal prep",
    "date night",
    "budget",
]

comment_phrases = [
    "I love Amir...",
    "Maksym is sooo handsome",
    "Ayan I am your stan",
    "Tunjay is such a cutie"
]

bio_phrases = [
    "home cook who loves quick meals",
    "always experimenting with new flavours",
    "meal prep enthusiast and pasta fan",
    "baking on weekends, cooking every day",
    "trying to eat healthier without losing taste",
    "big on comfort food and family dinners",
    "spice lover, especially in curries and stews",
    "student cook learning one recipe at a time",
    "foodie who believes butter fixes everything",
    "i cook, i taste, i improvise",
]

main_ingredients_pool = [
    "chicken breast", "salmon", "eggs", "milk", "butter", "cheddar",
    "onion", "garlic", "tomato", "bell pepper", "spinach", "mushrooms",
    "potatoes", "rice", "pasta", "flour", "yogurt", "lemon", "carrot",
    "broccoli", "canned beans", "chickpeas",
]

spices_pool = [
    "salt", "black pepper", "paprika", "cumin", "turmeric", "curry powder",
    "chilli flakes", "oregano", "basil", "thyme", "rosemary", "garam masala",
    "cinnamon", "nutmeg",
]


class Command(BaseCommand):
    """
    Build automation command to seed the database with data.

    This command inserts a small set of known users (``user_fixtures``) and then
    repeatedly generates additional random users until ``USER_COUNT`` total users
    exist in the database. Each generated user receives the same default password.

    Attributes:
        USER_COUNT (int): Target total number of users in the database.
        DEFAULT_PASSWORD (str): Default password assigned to all created users.
        help (str): Short description shown in ``manage.py help``.
        faker (Faker): Locale-specific Faker instance used for random data.
    """

    USER_COUNT = 200
    DEFAULT_PASSWORD = 'Password123'
    help = 'Seeds the database with sample data'

    def __init__(self, *args, **kwargs):
        """Initialize the command with a locale-specific Faker instance."""
        super().__init__(*args, **kwargs)
        self.faker = Faker('en_GB')

    def _make_uploaded_image(self, rel_path: str) -> SimpleUploadedFile:
        """
        rel_path should be like: "static/images/meal.jpg"
        """
        abs_path = os.path.join(settings.BASE_DIR, rel_path.lstrip("/"))
        with open(abs_path, "rb") as f:
            return SimpleUploadedFile(
                name=os.path.basename(abs_path),
                content=f.read(),
                content_type="image/jpeg",
            )

    def handle(self, *args, **options):
        """
        Django entrypoint for the command.

        Runs the full seeding workflow and stores ``self.users`` for any
        post-processing or debugging (not required for operation).
        """
        self.create_users()
        self.seed_followers_and_follows(follow_k=5)
        self.seed_recipe_posts(per_user=2)
        self.seed_recipe_steps(min_steps=4, max_steps=7)
        self.seed_favourites(per_user=2)
        self.seed_ingredients()
        self.seed_likes(max_likes_per_post=20)
        self.seed_comments(max_comments_per_post=5)
        self.users = User.objects.all()
        self.stdout.write(self.style.SUCCESS("Seeding complete"))

    def create_users(self):
        """
        Create fixture users and then generate random users up to USER_COUNT.

        The process is idempotent in spirit: attempts that fail (e.g., due to
        uniqueness constraints on username/email) are ignored and generation continues.
        """
        self.generate_user_fixtures()
        self.generate_random_users()

    def generate_user_fixtures(self):
        """Attempt to create each predefined fixture user."""
        for data in user_fixtures:
            self.try_create_user(data)

    def generate_random_users(self):
        """
        Generate random users until the database contains USER_COUNT users.

        Prints a simple progress indicator to stdout during generation.
        """
        user_count = User.objects.count()
        while  user_count < self.USER_COUNT:
            print(f"Seeding user {user_count}/{self.USER_COUNT}", end='\r')
            self.generate_user()
            user_count = User.objects.count()
        print("User seeding complete.      ")

    def generate_user(self):
        """
        Generate a single random user and attempt to insert it.

        Uses Faker for first/last names, then derives a simple username/email.
        """
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        email = create_email(first_name, last_name)
        username = create_username(first_name, last_name)
        self.try_create_user({'username': username, 'email': email, 'first_name': first_name, 'last_name': last_name})
       
    def try_create_user(self, data):
        """
        Attempt to create a user and ignore any errors.

        Args:
            data (dict): Mapping with keys ``username``, ``email``,
                ``first_name``, and ``last_name``.
        """
        try:
            self.create_user(data)
        except:
            pass

    def seed_followers_and_follows(self, follow_k: int = 5) -> None:
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
        user_ids = list(User.objects.values_list("id", flat=True))
        if not user_ids:
            return

        posts_to_create: List[RecipePost] = []
        images_to_create: List[RecipeImage] = []

        # IMPORTANT: these must be REAL files on disk for ImageField seeding
        # Example paths relative to BASE_DIR
        recipe_image_file_pool = [
            "static/images/meal1.jpg",
            "static/images/meal2.jpg",
            "static/images/meal3.jpg",
            "static/images/meal4.jpg",
            "static/images/meal5.jpg",
            "static/images/meal6.jpg",
            "static/images/meal7.jpg",
            "static/images/meal8.jpg",  
        ]

        for author_id in user_ids:
            count = randint(1, max(1, per_user))
            for _ in range(count):
                title = self.faker.sentence(nb_words=5).rstrip(".")[:255]
                description = self.faker.paragraph(nb_sentences=3)[:4000]
                image = choice(image_pool)  # your old string “cover” field
                prep = randint(0, 60)
                cook = randint(0, 90)
                tags = list(set(sample(tags_pool, randint(0, min(4, len(tags_pool))))))
                nutrition = f"kcal={randint(250, 800)}; protein={randint(5, 40)}g"
                category = choice(categories)

                post = RecipePost(
                    author_id=author_id,
                    title=title,
                    description=description,
                    image=image,
                    prep_time_min=prep,
                    cook_time_min=cook,
                    tags=tags,
                    nutrition=nutrition,
                    category=category,
                    saved_count=0,
                    published_at=timezone.now(),
                )
                posts_to_create.append(post)

                # Seed 2–4 images for each post (you can change this)
                img_count = randint(2, 4)
                chosen = sample(recipe_image_file_pool, k=min(img_count, len(recipe_image_file_pool)))

                for position, rel_path in enumerate(chosen):
                    try:
                        uploaded = self._make_uploaded_image(rel_path)
                    except FileNotFoundError:
                        # If the file doesn't exist locally, skip it (prevents seed crashing)
                        continue

                    images_to_create.append(
                        RecipeImage(
                            recipe_post_id=post.id,  # post.id exists already (UUID)
                            image=uploaded,
                            position=position,
                        )
                    )

        with transaction.atomic():
            RecipePost.objects.bulk_create(posts_to_create, ignore_conflicts=True, batch_size=500)
            RecipeImage.objects.bulk_create(images_to_create, ignore_conflicts=True, batch_size=500)

        self.stdout.write(f"Recipe posts created: {len(posts_to_create)}")
        self.stdout.write(f"Recipe images created (attempted): {len(images_to_create)}")
    
    def seed_recipe_steps(self, *, min_steps: int = 4, max_steps: int = 7) -> None:
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
        """
        seed likes for recipe posts.
        each post gets a random number of likes from random users.
        """
        users = list(User.objects.values_list("id", flat=True))
        posts = list(RecipePost.objects.values_list("id", flat=True))

        if not users or not posts:
            return

        rows = []

        for post_id in posts:
            like_count = randint(0, min(max_likes_per_post, len(users)))
            liked_by = sample(users, like_count)

            for user_id in liked_by:
                rows.append(
                    Like(
                        user_id=user_id,
                        recipe_post_id=post_id,
                    )
                )

        with transaction.atomic():
            Like.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)

        self.stdout.write(f"likes created: {len(rows)}")

    def seed_comments(self, max_comments_per_post: int = 5) -> None:
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
    

    def seed_ingredients(
    self,
    *,
    min_main: int = 4,
    max_main: int = 8,
    min_spices: int = 1,
    max_spices: int = 4,
) -> None:
        post_ids = list(RecipePost.objects.values_list("id", flat=True))
        if not post_ids:
            return

        rows: List[Ingredient] = []

        for post_id in post_ids:
            main_count = randint(min_main, max_main)
            spice_count = randint(min_spices, max_spices)

            mains = sample(main_ingredients_pool, k=min(main_count, len(main_ingredients_pool)))
            spices = sample(spices_pool, k=min(spice_count, len(spices_pool)))

            chosen = mains + spices
            position = 1

            for name in chosen:
                # randomly decide whether to add quantity/unit (optional fields)
                qty = None
                unit = None

                if randint(0, 1) == 1:
                    # simple, human-ish quantities
                    unit = choice(["g", "kg", "ml", "l", "tsp", "tbsp", "cup", "pinch", ""])
                    if unit == "pinch":
                        qty = None
                    elif unit in ("",):
                        qty = None
                        unit = None
                    else:
                        # keep >= 0
                        qty = choice([0.5, 1, 2, 3, 4, 100, 200, 250])

                rows.append(
                    Ingredient(
                        recipe_post_id=post_id,
                        name=name,
                        position=position,
                        quantity=qty,
                        unit=unit,
                    )
                )
                position += 1

        with transaction.atomic():
            Ingredient.objects.bulk_create(rows, ignore_conflicts=True, batch_size=1000)

        self.stdout.write(f"ingredients created (attempted): {len(rows)}")
    
    
    
    def seed_favourites(self, *, per_user: int = 2) -> None:
        """
        for each user, create 2 favourites (collections) from a predefined set,
        then add random existing recipe posts into each favourite.
        """
        user_ids = list(User.objects.values_list("id", flat=True))
        if not user_ids:
            return

        posts = list(RecipePost.objects.values_list("id", flat=True))
        if not posts:
            self.stdout.write("no recipe posts found, skipping favourites seeding.")
            return

        # clamp to available names
        collections_per_user = min(per_user, len(favourite_names))

        favourites_to_create: List[Favourite] = []
        fav_keys: Set[Tuple[str, str]] = set()  # (user_id, name)

        # 1) create favourites (collections)
        for user_id in user_ids:
            chosen = sample(favourite_names, k=collections_per_user)
            for name in chosen:
                key = (str(user_id), name)
                if key in fav_keys:
                    continue
                fav_keys.add(key)
                favourites_to_create.append(Favourite(user_id=user_id, name=name))

        with transaction.atomic():
            Favourite.objects.bulk_create(
                favourites_to_create,
                ignore_conflicts=True,
                batch_size=500
            )

        # fetch favourites back (we need their ids for items)
        favourites = list(
            Favourite.objects.filter(user_id__in=user_ids).values_list("id", "user_id")
        )

        # group favourite ids by user for easy random assignment
        favs_by_user: Dict[str, List[str]] = {}
        for fav_id, u_id in favourites:
            favs_by_user.setdefault(str(u_id), []).append(str(fav_id))

        # 2) add random posts into each favourite
        items_to_create: List[FavouriteItem] = []

        for user_id in user_ids:
            user_fav_ids = favs_by_user.get(str(user_id), [])
            if not user_fav_ids:
                continue

            for fav_id in user_fav_ids:
                # choose how many posts to add to this collection
                k = randint(3, 8)
                chosen_posts = sample(posts, k=min(k, len(posts)))

                for post_id in chosen_posts:
                    items_to_create.append(
                        FavouriteItem(favourite_id=fav_id, recipe_post_id=post_id)
                    )

        with transaction.atomic():
            FavouriteItem.objects.bulk_create(
                items_to_create,
                ignore_conflicts=True,
                batch_size=1000
            )

        self.stdout.write(
            f"favourites seeded: {len(favourites_to_create)} collections, {len(items_to_create)} items attempted"
        )
    def create_user(self, data):
        """
        Create a user with the default password.

        Args:
            data (dict): Mapping with keys ``username``, ``email``,
                ``first_name``, and ``last_name``.
        """
        User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=Command.DEFAULT_PASSWORD,
            first_name=data['first_name'],
            last_name=data['last_name'],
            bio = choice(bio_phrases)
        )

def create_username(first_name, last_name):
    """
    Construct a simple username from first and last names.

    Args:
        first_name (str): Given name.
        last_name (str): Family name.

    Returns:
        str: A username in the form ``@{firstname}{lastname}`` (lowercased).
    """
    return '@' + first_name.lower() + last_name.lower()

def create_email(first_name, last_name):
    """
    Construct a simple example email address.

    Args:
        first_name (str): Given name.
        last_name (str): Family name.

    Returns:
        str: An email in the form ``{firstname}.{lastname}@example.org``.
    """
    return first_name + '.' + last_name + '@example.org'
