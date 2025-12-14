from django.test import TestCase
from django.db import IntegrityError

from recipes.models.like import Like
from recipes.tests.helpers import make_user, make_recipe_post


class LikeModelTestCase(TestCase):
    def setUp(self):
        self.user_a = make_user(username="@usera")
        self.user_b = make_user(username="@userb")
        self.post = make_recipe_post(author=self.user_a)

    def test_user_can_like_a_post(self):
        like = Like.objects.create(user=self.user_b, recipe_post=self.post)

        self.assertEqual(like.user, self.user_b)
        self.assertEqual(like.recipe_post, self.post)
        self.assertEqual(Like.objects.count(), 1)

    def test_like_exists_check(self):
        self.assertFalse(
            Like.objects.filter(user=self.user_b, recipe_post=self.post).exists()
        )

        Like.objects.create(user=self.user_b, recipe_post=self.post)

        self.assertTrue(
            Like.objects.filter(user=self.user_b, recipe_post=self.post).exists()
        )

    def test_can_count_likes_for_post(self):
        Like.objects.create(user=self.user_b, recipe_post=self.post)
        Like.objects.create(user=self.user_a, recipe_post=self.post)

        self.assertEqual(Like.objects.filter(recipe_post=self.post).count(), 2)

    def test_duplicate_like_not_allowed_if_unique_constraint_exists(self):
        """
        If your Like model has a unique constraint on (user, recipe_post),
        this should raise IntegrityError.
        If you don't have that constraint, delete this test.
        """
        Like.objects.create(user=self.user_b, recipe_post=self.post)

        with self.assertRaises(IntegrityError):
            Like.objects.create(user=self.user_b, recipe_post=self.post)

    def test_string_representation(self):
        like = Like.objects.create(user=self.user_b, recipe_post=self.post)
        # Don’t assume exact formatting; just ensure it’s a non-empty string.
        self.assertTrue(str(like))