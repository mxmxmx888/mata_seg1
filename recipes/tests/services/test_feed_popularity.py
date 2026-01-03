from types import SimpleNamespace
from django.test import TestCase

from recipes.services.feed import FeedService


class FeedServicePopularityTests(TestCase):
    def test_resolved_likes_prefers_likes_total(self):
        post = SimpleNamespace(saved_count=0, _likes_total=5)
        svc = FeedService()
        self.assertEqual(svc._popularity_score(post), 5)

    def test_count_relationship_likes_handles_missing_attr(self):
        post = SimpleNamespace(saved_count=1)
        svc = FeedService()
        self.assertEqual(svc._popularity_score(post), 1)
