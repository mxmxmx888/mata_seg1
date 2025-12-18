from unittest.mock import patch
from django.test import TestCase
from recipes.models import User, RecipePost, Follows
from recipes.repos.post_repo import PostRepo

class PostRepoTestCase(TestCase):
    fixtures = [
        "recipes/tests/fixtures/default_user.json",
        "recipes/tests/fixtures/other_users.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username="@johndoe")
        self.other = User.objects.get(username="@janedoe")
        self.repo = PostRepo()
        RecipePost.objects.create(
            author=self.user,
            title="Soup",
            description="veg",
            category="Dinner",
        )
        RecipePost.objects.create(
            author=self.other,
            title="Toast",
            description="yum",
            category="breakfast",
        )

    def test_list_ids_has_values(self):
        ids = self.repo.list_ids()
        self.assertEqual(len(ids), 2)

    def test_list_for_feed_filters(self):
        qs = self.repo.list_for_feed(category="DINNER", author_id=self.user.id, limit=1, offset=0)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().title, "Soup")

    def test_list_for_feed_no_filters(self):
        qs = self.repo.list_for_feed()
        self.assertEqual(qs.count(), 2)
        qs_all = self.repo.list_for_feed(category="all")
        self.assertEqual(qs_all.count(), 2)

    def test_list_for_feed_limit_and_offset(self):
        qs = self.repo.list_for_feed(limit=1)
        self.assertEqual(qs.count(), 1)
        qs_offset = self.repo.list_for_feed(limit=1, offset=1)
        self.assertEqual(qs_offset.count(), 1)

    def test_list_for_user_calls_feed(self):
        qs = self.repo.list_for_user(self.other.id)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().author, self.other)

    def test_list_for_following_handles_branches(self):
        from recipes import models as model_pkg
        model_pkg.Post = type("Post", (), {"objects": RecipePost.objects})()
        self.repo.list_for_feed = lambda *args, **kwargs: RecipePost.objects.all()
        none_list = self.repo.list_for_following(self.user.id, limit=1)
        self.assertEqual(list(none_list), [])

        Follows.objects.create(author=self.user, followee=self.other)
        feed = self.repo.list_for_following(self.user.id, limit=5)
        titles = [p.title for p in feed]
        self.assertIn("Toast", titles)

    def test_list_for_following_uses_none_when_no_post_model(self):
        from recipes import models as model_pkg
        model_pkg.Post = type("Post", (), {"objects": type("Mgr", (), {"none": lambda self: []})()})()
        Follows.objects.filter(author_id=self.user.id).delete()
        result = self.repo.list_for_following(self.user.id, limit=1)
        self.assertEqual(list(result), [])

    def test_list_for_following_without_list_for_feed_uses_list_all(self):
        class NoFeedRepo:
            def list_all(self):
                return RecipePost.objects.all()
        NoFeedRepo.list_for_following = PostRepo.list_for_following
        repo = NoFeedRepo()
        Follows.objects.create(author=self.user, followee=self.other)
        RecipePost.objects.create(author=self.other, title="Rice", description="d")
        try:
            feed = repo.list_for_following(self.user.id, limit=2)
        except Exception as exc:
            self.fail(str(exc))
        self.assertTrue(list(feed))
