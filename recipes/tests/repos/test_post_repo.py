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

        self.soup = RecipePost.objects.create(
            author=self.user,
            title="Soup",
            description="veg",
            category="Dinner",
        )
        self.toast = RecipePost.objects.create(
            author=self.other,
            title="Toast",
            description="yum",
            category="breakfast",
        )

    def test_list_ids_has_values(self):
        ids = list(self.repo.list_ids())
        self.assertEqual(len(ids), 2)
        self.assertIn(self.soup.id, ids)
        self.assertIn(self.toast.id, ids)

    def test_list_ids_empty_when_no_posts(self):
        RecipePost.objects.all().delete()
        ids = list(self.repo.list_ids())
        self.assertEqual(ids, [])

    def test_list_all_returns_all_posts(self):
        """Covers PostRepo.list_all if it exists."""
        if not hasattr(self.repo, "list_all"):
            self.skipTest("PostRepo has no list_all method.")
        qs = self.repo.list_all()
        self.assertEqual(qs.count(), 2)
        titles = {p.title for p in qs}
        self.assertEqual(titles, {"Soup", "Toast"})

    def test_list_all_with_no_posts_returns_empty_qs(self):
        """Covers PostRepo.list_all with empty table."""
        if not hasattr(self.repo, "list_all"):
            self.skipTest("PostRepo has no list_all method.")
        RecipePost.objects.all().delete()
        qs = self.repo.list_all()
        self.assertEqual(qs.count(), 0)

    def test_list_for_feed_filters_category_and_author(self):
        qs = self.repo.list_for_feed(
            category="DINNER",  # case-insensitive
            author_id=self.user.id,
            limit=1,
            offset=0,
        )
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().title, "Soup")

    def test_list_for_feed_no_filters(self):
        qs = self.repo.list_for_feed()
        self.assertEqual(qs.count(), 2)

        qs_all = self.repo.list_for_feed(category="all")
        self.assertEqual(qs_all.count(), 2)

    def test_list_for_feed_filters_by_author_only(self):
        qs = self.repo.list_for_feed(author_id=self.other.id)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().author, self.other)
        self.assertEqual(qs.first().title, "Toast")

    def test_list_for_feed_limit_and_offset(self):
        qs = self.repo.list_for_feed(limit=1)
        self.assertEqual(qs.count(), 1)

        qs_offset = self.repo.list_for_feed(limit=1, offset=1)
        self.assertEqual(qs_offset.count(), 1)

        # Ensure the offset actually changes which object we see
        titles = {p.title for p in qs.union(qs_offset)}
        self.assertEqual(titles, {"Soup", "Toast"})

    def test_list_for_feed_offset_without_limit_returns_slice(self):
        qs = self.repo.list_for_feed(offset=1)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().title, "Toast")

    def test_list_for_user_calls_feed_for_that_user(self):
        qs = self.repo.list_for_user(self.other.id)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().author, self.other)
        self.assertEqual(qs.first().title, "Toast")

    def test_list_for_user_with_limit_and_offset(self):
        # Make another post for self.other to ensure slicing happens
        extra = RecipePost.objects.create(
            author=self.other,
            title="Rice",
            description="d",
            category="dinner",
        )
        qs = self.repo.list_for_user(self.other.id, limit=1)
        self.assertEqual(qs.count(), 1)

        qs_offset = self.repo.list_for_user(self.other.id, limit=1, offset=1)
        self.assertEqual(qs_offset.count(), 1)
        titles = {p.title for p in qs.union(qs_offset)}
        self.assertEqual(titles, {"Toast", "Rice"})

    def test_list_for_following_handles_branches(self):
        from recipes import models as model_pkg

        model_pkg.Post = type(
            "Post",
            (),
            {"objects": RecipePost.objects},
        )()

        self.repo.list_for_feed = lambda *args, **kwargs: RecipePost.objects.all()
        none_list = self.repo.list_for_following(self.user.id, limit=1)
        self.assertEqual(list(none_list), [])

        Follows.objects.create(author=self.user, followee=self.other)
        feed_titles = [p.title for p in self.repo.list_for_following(self.user.id, limit=5)]
        self.assertIn("Toast", feed_titles)

    def test_list_for_following_uses_none_when_no_post_model(self):
        from recipes import models as model_pkg

        # Ensure there is NO Post attribute to trigger the "no model" path
        if hasattr(model_pkg, "Post"):
            delattr(model_pkg, "Post")

        Follows.objects.filter(author_id=self.user.id).delete()
        result = self.repo.list_for_following(self.user.id, limit=1)
        self.assertEqual(list(result), [])

    def test_list_for_following_without_list_for_feed_uses_list_all(self):
        class NoFeedRepo:
            def list_all(self):
                return RecipePost.objects.all()

        # Attach PostRepo.list_for_following as an unbound function
        NoFeedRepo.list_for_following = PostRepo.list_for_following

        repo = NoFeedRepo()
        Follows.objects.create(author=self.user, followee=self.other)
        RecipePost.objects.create(
            author=self.other,
            title="Rice",
            description="d",
            category="dinner",
        )

        try:
            feed = repo.list_for_following(self.user.id, limit=2)
        except Exception as exc:
            self.fail(f"list_for_following raised unexpectedly: {exc}")

        self.assertTrue(list(feed))

    def test_list_for_following_without_feed_or_list_all_uses_model(self):
        class MinimalRepo:
            model = RecipePost

        MinimalRepo.list_for_following = PostRepo.list_for_following

        repo = MinimalRepo()
        Follows.objects.create(author=self.user, followee=self.other)

        qs = repo.list_for_following(self.user.id, limit=1)
        self.assertEqual(qs.count(), 1)
