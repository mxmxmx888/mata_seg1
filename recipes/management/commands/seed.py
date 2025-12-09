"""
Management command to seed the database with demo data.

This command creates a small set of named fixture users and then fills up
to ``USER_COUNT`` total users using Faker-generated data. Existing records
are left untouched—if a create fails (e.g., due to duplicates), the error
is swallowed and generation continues.
"""


from typing import Any, Dict, List, Set, Tuple
from random import sample, randint, choice
from uuid import uuid4

from faker import Faker
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from recipes.models import User
from recipes.models.followers import Follower
from recipes.models.follows import Follows
from recipes.models.recipe_post import RecipePost



user_fixtures = [
    {'username': '@johndoe', 'email': 'john.doe@example.org', 'first_name': 'John', 'last_name': 'Doe'},
    {'username': '@janedoe', 'email': 'jane.doe@example.org', 'first_name': 'Jane', 'last_name': 'Doe'},
    {'username': '@charlie', 'email': 'charlie.johnson@example.org', 'first_name': 'Charlie', 'last_name': 'Johnson'},
]

categories = ["Breakfast", "Lunch", "Dinner", "Dessert", "Vegan"]
tags_pool = ["quick", "family", "spicy", "budget", "comfort", "healthy", "high_protein", "low_carb"]


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

    def handle(self, *args, **options):
        """
        Django entrypoint for the command.

        Runs the full seeding workflow and stores ``self.users`` for any
        post-processing or debugging (not required for operation).
        """
        self.create_users()
        self.seed_followers_and_follows(follow_k=5)
        self.seed_recipe_posts(per_user=2)
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

        rows: List[RecipePost] = []
        for author_id in user_ids:
            count = randint(1, max(1, per_user))
            for _ in range(count):
                title = self.faker.sentence(nb_words=5).rstrip(".")[:255]
                description = self.faker.paragraph(nb_sentences=3)[:4000]
                image = f"https://picsum.photos/seed/{uuid4()}/800/600"  
                prep = randint(0, 60)
                cook = randint(0, 90)
                tags = list(set(sample(tags_pool, randint(0, min(4, len(tags_pool))))))
                nutrition = f"kcal={randint(250, 800)}; protein={randint(5, 40)}g"
                category = choice(categories)

                rows.append(RecipePost(
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
                ))

        RecipePost.objects.bulk_create(rows, ignore_conflicts=True, batch_size=500)
        self.stdout.write(f"Recipe posts created: {len(rows)}")

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
