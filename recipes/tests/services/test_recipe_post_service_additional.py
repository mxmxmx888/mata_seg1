from types import SimpleNamespace
from django.test import TestCase

from recipes.services.recipe_posts import (
    RecipeContentService,
    RecipeEngagementService,
    RecipePostService,
)


class RecipeEngagementServiceAdditionalTests(TestCase):
    def test_maybe_update_latest_handles_none(self):
        svc = RecipeEngagementService()
        now = 5  # simple comparable sentinel

        self.assertEqual(svc._maybe_update_latest(None, now), now)
        self.assertEqual(svc._maybe_update_latest(now, None), now)
        self.assertEqual(svc._maybe_update_latest(now, 3), now)

    def test_valid_saved_post_skips_duplicates(self):
        svc = RecipeEngagementService()
        seen = set()
        post = SimpleNamespace(id=1)
        item = SimpleNamespace(recipe_post=post)

        first = svc._valid_saved_post(item, seen)
        second = svc._valid_saved_post(item, seen)

        self.assertIs(first, post)
        self.assertIsNone(second)


class RecipePostServiceShimTests(TestCase):
    def test_init_sets_service_helpers(self):
        svc = RecipePostService()

        self.assertIsInstance(svc.content, RecipeContentService)
        self.assertIsInstance(svc.engagement, RecipeEngagementService)

    def test_getattr_delegates_and_errors_for_missing(self):
        svc = RecipePostService()
        svc.engagement.sample = object()
        svc.content.sample = object()

        self.assertIs(svc.sample, svc.engagement.sample)

        svc.content.only_here = "content"
        self.assertEqual(svc.only_here, "content")

        with self.assertRaises(AttributeError) as exc:
            svc.not_available

        self.assertIn("RecipePostService has no attribute not_available", str(exc.exception))
