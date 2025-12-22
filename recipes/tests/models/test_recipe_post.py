from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from recipes.models import User, Like
from recipes.models.recipe_post import RecipePost, RecipeImage
from recipes.tests.helpers import make_user, make_recipe_post


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

    def test_primary_image_url_returns_recipe_image_url(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="with image",
            description="desc",
        )
        file = SimpleUploadedFile("test.jpg", b"data", content_type="image/jpeg")
        image = RecipeImage.objects.create(recipe_post=post, image=file, position=0)

        self.assertEqual(post.primary_image_url, image.image.url)

    def test_primary_image_url_handles_first_image_value_error(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="with bad image",
            description="desc",
        )
        class BadImage:
            @property
            def url(self):
                raise ValueError("bad")
        bad = SimpleNamespace(image=BadImage())
        mock_manager = SimpleNamespace(first=lambda: bad)
        with patch.object(RecipePost, "images", new_callable=PropertyMock, return_value=mock_manager):
            post.image = "legacy.jpg"
            self.assertEqual(post.primary_image_url, "legacy.jpg")

    def test_primary_image_url_falls_back_to_legacy_image(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="legacy",
            description="desc",
            image="legacy.jpg",
        )
        class BadImage:
            @property
            def url(self):
                raise ValueError("bad")
        bad_image = SimpleNamespace(image=BadImage())
        mock_manager = SimpleNamespace(first=lambda: bad_image)
        with patch.object(RecipePost, "images", new_callable=PropertyMock, return_value=mock_manager):
            self.assertEqual(post.primary_image_url, "legacy.jpg")

    def test_primary_image_url_none_when_no_images(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="no image",
            description="desc",
        )
        mock_manager = SimpleNamespace(first=lambda: None)
        with patch.object(RecipePost, "images", new_callable=PropertyMock, return_value=mock_manager):
            post.image = ""
            self.assertIsNone(post.primary_image_url)

    def test_primary_image_url_uses_property_mock_manager(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="mocked manager",
            description="desc",
        )
        mock_manager = SimpleNamespace(first=lambda: SimpleNamespace(image=SimpleNamespace(url="http://example.com/one.jpg")))
        with patch.object(RecipePost, "images", new_callable=PropertyMock, return_value=mock_manager):
            self.assertEqual(post.primary_image_url, "http://example.com/one.jpg")

    def test_primary_image_url_returns_legacy_when_manager_none(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="manager none",
            description="desc",
            image="legacy.jpg",
        )
        with patch.object(RecipePost, "images", new_callable=PropertyMock, return_value=None):
            self.assertEqual(post.primary_image_url, "legacy.jpg")

    def test_primary_image_url_skips_when_first_has_no_image(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="no first image",
            description="desc",
        )
        mock_first = SimpleNamespace(image=None)
        mock_manager = SimpleNamespace(first=lambda: mock_first)
        with patch.object(RecipePost, "images", new_callable=PropertyMock, return_value=mock_manager):
            self.assertIsNone(post.primary_image_url)

    def test_likes_count_property(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="likeable",
            description="desc",
        )
        Like.objects.create(user=self.user, recipe_post=post)
        self.assertEqual(post.likes_count, 1)

    def test_recipe_image_str(self):
        post = RecipePost.objects.create(
            author=self.user,
            title="with image str",
            description="desc",
        )
        file = SimpleUploadedFile("str.jpg", b"data", content_type="image/jpeg")
        image = RecipeImage.objects.create(recipe_post=post, image=file, position=0)
        self.assertIn(str(post.id), str(image))
