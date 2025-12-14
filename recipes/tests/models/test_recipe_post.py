from django.test import TestCase
from recipes.tests.helpers import make_user, make_recipe_post
from django.utils import timezone

from recipes.models import User, RecipePost


class RecipePostModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="@tester",
            email="tester@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
            bio="testing bio",
        )

    def test_can_create_minimal_recipe_post(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="my post",
            description="hello",
        )
        self.assertIsNotNone(post.id)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.title, "my post")
        self.assertEqual(post.description, "hello")

    def test_defaults_are_set(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="defaults",
            description="checking defaults",
        )
        # defaults in your model
        self.assertEqual(post.prep_time_min, 0)
        self.assertEqual(post.cook_time_min, 0)
        self.assertEqual(post.tags, [])
        self.assertEqual(post.saved_count, 0)
        self.assertIsNone(post.published_at)
        self.assertFalse(post.is_hidden)
        # optional fields
        self.assertIsNone(post.image)
        self.assertIsNone(post.nutrition)
        self.assertIsNone(post.category)

    def test_created_at_and_updated_at_are_set(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="timestamps",
            description="check timestamps",
        )
        self.assertIsNotNone(post.created_at)
        self.assertIsNotNone(post.updated_at)

    def test_updated_at_changes_on_save(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="timestamps 2",
            description="check updated_at",
        )
        old_updated = post.updated_at
        post.title = "changed"
        post.save()
        post.refresh_from_db()
        self.assertGreaterEqual(post.updated_at, old_updated)

    def test_str_returns_title(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="nice title",
            description="desc",
        )
        self.assertEqual(str(post), "nice title")

    def test_db_table_name(self):
        self.assertEqual(RecipePost._meta.db_table, "recipe_post")

    def test_can_publish(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="publish me",
            description="desc",
            published_at=timezone.now(),
        )
        self.assertIsNotNone(post.published_at)