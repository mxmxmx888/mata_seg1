from types import SimpleNamespace
from django.test import TestCase

from recipes.services.recipe_posts import RecipePostService


class RecipePostServiceAdditionalTests(TestCase):
    def test_maybe_update_latest_handles_none(self):
        svc = RecipePostService()
        now = 5  # simple comparable sentinel

        self.assertEqual(svc._maybe_update_latest(None, now), now)
        self.assertEqual(svc._maybe_update_latest(now, None), now)
        self.assertEqual(svc._maybe_update_latest(now, 3), now)

    def test_valid_saved_post_skips_duplicates(self):
        svc = RecipePostService()
        seen = set()
        post = SimpleNamespace(id=1)
        item = SimpleNamespace(recipe_post=post)

        first = svc._valid_saved_post(item, seen)
        second = svc._valid_saved_post(item, seen)

        self.assertIs(first, post)
        self.assertIsNone(second)
