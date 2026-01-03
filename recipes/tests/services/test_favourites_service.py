from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase

from recipes.services.favourites import FavouriteService


class FavouriteServiceTests(TestCase):
    def test_posts_for_orders_and_filters(self):
        item_with_post = SimpleNamespace(recipe_post="post", added_at=2, id=1)
        item_without_post = SimpleNamespace(recipe_post=None, added_at=3, id=2)
        qs = MagicMock()
        qs.filter.return_value = qs
        qs.select_related.return_value = qs
        qs.order_by.return_value = [item_with_post, item_without_post]

        svc = FavouriteService(favourite_item_model=MagicMock(objects=MagicMock(filter=MagicMock(return_value=qs))))

        posts = svc.posts_for("fav")

        svc.favourite_item_model.objects.filter.assert_called_once_with(favourite="fav")
        qs.order_by.assert_called_once()
        self.assertEqual(posts, ["post"])

    def test_list_for_user_prefetches_related(self):
        qs = MagicMock()
        qs.prefetch_related.return_value = "prefetched"
        fav_model = MagicMock()
        fav_model.objects.filter.return_value = qs
        svc = FavouriteService(favourite_model=fav_model, favourite_item_model=MagicMock())

        result = svc.list_for_user("user")

        fav_model.objects.filter.assert_called_once_with(user="user")
        qs.prefetch_related.assert_called_once_with("items__recipe_post")
        self.assertEqual(result, "prefetched")

    def test_fetch_for_user_uses_get_object_or_404(self):
        svc = FavouriteService(favourite_model="Favourite", favourite_item_model=MagicMock())

        with patch("recipes.services.favourites.get_object_or_404") as gof:
            svc.fetch_for_user("slug", "user")
            gof.assert_called_once_with("Favourite", id="slug", user="user")

    def test_update_name_and_delete(self):
        fav = SimpleNamespace(name="old", save=MagicMock(), delete=MagicMock())
        svc = FavouriteService(favourite_item_model=MagicMock())

        updated = svc.update_name(fav, "new")
        self.assertEqual(updated.name, "new")
        fav.save.assert_called_once_with(update_fields=["name"])

        svc.delete(fav)
        fav.delete.assert_called_once()
