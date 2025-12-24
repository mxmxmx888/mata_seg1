from django.db import IntegrityError
from django.test import TestCase

from recipes.models.favourite import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.tests.test_utils import make_user, make_recipe_post


class FavouriteModelTestCase(TestCase):
    def setUp(self):
        self.user = make_user(username="@alice")
        self.other_user = make_user(username="@bob")

        self.post1 = make_recipe_post(author=self.user)
        self.post2 = make_recipe_post(author=self.other_user)

    def test_user_can_create_favourite_collection(self):
        fav = Favourite.objects.create(user=self.user, name="favourites")
        self.assertEqual(fav.user, self.user)
        self.assertEqual(fav.name, "favourites")

    def test_same_user_cannot_have_duplicate_collection_name_if_unique(self):
        """
        If your Favourite model enforces uniqueness on (user, name),
        this should raise IntegrityError. If not enforced, delete this test.
        """
        Favourite.objects.create(user=self.user, name="favourites")
        with self.assertRaises(IntegrityError):
            Favourite.objects.create(user=self.user, name="favourites")

    def test_different_users_can_use_same_collection_name(self):
        Favourite.objects.create(user=self.user, name="favourites")
        Favourite.objects.create(user=self.other_user, name="favourites")
        self.assertEqual(Favourite.objects.filter(name="favourites").count(), 2)

    def test_can_add_items_to_favourite(self):
        fav = Favourite.objects.create(user=self.user, name="dinner ideas")

        FavouriteItem.objects.create(favourite=fav, recipe_post=self.post1)
        FavouriteItem.objects.create(favourite=fav, recipe_post=self.post2)

        self.assertEqual(FavouriteItem.objects.filter(favourite=fav).count(), 2)

        post_ids = set(
            FavouriteItem.objects.filter(favourite=fav).values_list("recipe_post_id", flat=True)
        )
        self.assertEqual(post_ids, {self.post1.id, self.post2.id})

    def test_string_representation(self):
        fav = Favourite.objects.create(user=self.user, name="meal prep")
        s = str(fav)
        self.assertTrue(isinstance(s, str))
        self.assertTrue(len(s) > 0)