from types import SimpleNamespace
from django.test import TestCase

from recipes.services.feed import FeedService


class FeedServiceAdditionalTests(TestCase):
    def test_popularity_score_uses_likes_count_when_present(self):
        svc = FeedService()
        post = SimpleNamespace(saved_count=3, likes_count=2)

        score = svc._popularity_score(post)

        self.assertEqual(score, 5)

    def test_popularity_score_handles_like_count_exception(self):
        class LikesWrapper:
            def count(self):
                raise Exception("db error")

        post = SimpleNamespace(saved_count=1, likes=LikesWrapper())
        svc = FeedService()

        score = svc._popularity_score(post)

        self.assertEqual(score, 1)
