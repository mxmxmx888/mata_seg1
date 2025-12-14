from django.db import IntegrityError
from django.test import TestCase

from recipes.models.favourite import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.tests.helpers import make_user, make_recipe_post


class FavouriteItemModelTestCase(TestCase):
    def setUp(self):
        self.user = make_user(username="@alice")
        self.post = make_recipe_post(author=self.user)
        self.fav = Favourite.objects.create(user=self.user, name="favourites")

    def test_user_can_add_post_to_favourite(self):
        item = FavouriteItem.objects.create(favourite=self.fav, recipe_post=self.post)
        self.assertEqual(item.favourite, self.fav)
        self.assertEqual(item.recipe_post, self.post)

    def test_favourite_can_have_multiple_items(self):
        post2 = make_recipe_post(author=self.user)
        FavouriteItem.objects.create(favourite=self.fav, recipe_post=self.post)
        FavouriteItem.objects.create(favourite=self.fav, recipe_post=post2)

        self.assertEqual(FavouriteItem.objects.filter(favourite=self.fav).count(), 2)

    def test_same_post_can_be_in_multiple_favourites(self):
        fav2 = Favourite.objects.create(user=self.user, name="dinner ideas")
        FavouriteItem.objects.create(favourite=self.fav, recipe_post=self.post)
        FavouriteItem.objects.create(favourite=fav2, recipe_post=self.post)

        self.assertEqual(FavouriteItem.objects.filter(recipe_post=self.post).count(), 2)

    def test_duplicate_item_not_allowed_if_unique_together(self):
        """
        If FavouriteItem enforces uniqueness on (favourite, recipe_post),
        the second insert should raise IntegrityError.
        If your model does NOT enforce it, delete this test.
        """
        FavouriteItem.objects.create(favourite=self.fav, recipe_post=self.post)
        with self.assertRaises(IntegrityError):
            FavouriteItem.objects.create(favourite=self.fav, recipe_post=self.post)

    def test_string_representation(self):
        item = FavouriteItem.objects.create(favourite=self.fav, recipe_post=self.post)
        s = str(item)
        self.assertTrue(isinstance(s, str))
        self.assertTrue(len(s) > 0)