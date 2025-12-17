from django.test import TestCase
from recipes.models import User, Follower, CloseFriend, RecipePost
from recipes.services import PrivacyService

class PrivacyServiceTestCase(TestCase):
    fixtures = [
        "recipes/tests/fixtures/default_user.json",
        "recipes/tests/fixtures/other_users.json",
    ]

    def setUp(self):
        self.viewer = User.objects.get(username="@johndoe")
        self.author = User.objects.get(username="@janedoe")
        self.other = User.objects.get(username="@petrapickles")
        self.author.is_private = True
        self.author.save()
        self.service = PrivacyService()
        self.public_post = RecipePost.objects.create(author=self.other, title="pub", description="d", visibility=RecipePost.VISIBILITY_PUBLIC)
        self.followers_post = RecipePost.objects.create(author=self.author, title="fol", description="d", visibility=RecipePost.VISIBILITY_FOLLOWERS)
        self.close_post = RecipePost.objects.create(author=self.author, title="close", description="d", visibility=RecipePost.VISIBILITY_CLOSE_FRIENDS)

    def test_is_private_checks_flag(self):
        self.assertTrue(self.service.is_private(self.author))
        self.assertFalse(self.service.is_private(self.viewer))

    def test_can_view_profile_public_user(self):
        public = self.other
        public.is_private = False
        self.assertTrue(self.service.can_view_profile(self.viewer, public))

    def test_is_follower_and_close_friend(self):
        self.assertTrue(self.service.is_follower(self.viewer, self.viewer))
        Follower.objects.create(follower=self.viewer, author=self.author)
        CloseFriend.objects.create(owner=self.author, friend=self.viewer)
        self.assertTrue(self.service.is_follower(self.viewer, self.author))
        self.assertTrue(self.service.is_close_friend(self.viewer, self.author))

    def test_is_close_friend_self(self):
        self.assertTrue(self.service.is_close_friend(self.viewer, self.viewer))

    def test_can_view_profile_respects_privacy(self):
        result = self.service.can_view_profile(self.viewer, self.author)
        self.assertFalse(result)
        Follower.objects.create(follower=self.viewer, author=self.author)
        self.assertTrue(self.service.can_view_profile(self.viewer, self.author))

    def test_can_view_post_by_visibility(self):
        self.assertTrue(self.service.can_view_post(self.other, self.public_post))
        self.assertFalse(self.service.can_view_post(self.viewer, self.followers_post))
        Follower.objects.create(follower=self.viewer, author=self.author)
        self.assertTrue(self.service.can_view_post(self.viewer, self.followers_post))
        CloseFriend.objects.create(owner=self.author, friend=self.viewer)
        self.assertTrue(self.service.can_view_post(self.viewer, self.close_post))

    def test_filter_visible_posts_limits_results(self):
        Follower.objects.create(follower=self.viewer, author=self.author)
        qs = RecipePost.objects.filter(author__in=[self.author, self.other])
        seen = self.service.filter_visible_posts(qs, self.viewer)
        titles = set(p.title for p in seen)
        self.assertIn("pub", titles)
        self.assertIn("fol", titles)

    def test_filter_visible_posts_for_guest(self):
        qs = RecipePost.objects.all()
        guest = type("Anon", (), {"is_authenticated": False})()
        visible = self.service.filter_visible_posts(qs, guest)
        titles = [p.title for p in visible]
        self.assertIn("pub", titles)
        self.assertNotIn("fol", titles)

    def test_can_view_post_blocks_private_non_follower(self):
        viewer = User.objects.get(username="@peterpickles")
        blocked = self.service.can_view_post(viewer, self.followers_post)
        self.assertFalse(blocked)

    def test_is_follower_returns_false_when_logged_out(self):
        anon = type("Anon", (), {"is_authenticated": False})()
        self.assertFalse(self.service.is_follower(anon, self.author))

    def test_can_view_post_close_friends_only(self):
        stranger = User.objects.get(username="@peterpickles")
        post = RecipePost.objects.create(author=self.author, title="cf", description="d", visibility=RecipePost.VISIBILITY_CLOSE_FRIENDS)
        self.assertFalse(self.service.can_view_post(stranger, post))

    def test_filter_visible_posts_guest_only_public(self):
        guest = None
        qs = RecipePost.objects.all()
        seen = self.service.filter_visible_posts(qs, guest)
        titles = [p.title for p in seen]
        self.assertEqual(titles, ["pub"])

    def test_is_close_friend_false_for_anon(self):
        anon = type("Anon", (), {"is_authenticated": False})()
        self.assertFalse(self.service.is_close_friend(anon, self.author))

    def test_author_always_sees_own_post(self):
        post = RecipePost.objects.create(author=self.viewer, title="mine", description="d", visibility=RecipePost.VISIBILITY_CLOSE_FRIENDS)
        self.assertTrue(self.service.can_view_post(self.viewer, post))

    def test_unknown_visibility_returns_false(self):
        post = RecipePost.objects.create(author=self.other, title="odd", description="d")
        post.visibility = "mystery"
        try:
            can_view = self.service.can_view_post(self.viewer, post)
        except Exception as exc:
            self.fail(f"Unexpected error {exc}")
        self.assertFalse(can_view)

    def test_filter_visible_posts_includes_own_private(self):
        self.author.is_private = True
        self.author.save()
        private_post = RecipePost.objects.create(author=self.author, title="secret", description="d", visibility=RecipePost.VISIBILITY_FOLLOWERS)
        seen = self.service.filter_visible_posts(RecipePost.objects.filter(id=private_post.id), self.author)
        self.assertIn(private_post, list(seen))

    def test_can_view_profile_false_for_guest_on_private(self):
        guest = type("Anon", (), {"is_authenticated": False})()
        self.assertFalse(self.service.can_view_profile(guest, self.author))

    def test_filter_excludes_private_for_non_follower(self):
        secret = RecipePost.objects.create(author=self.author, title="hide", description="d", visibility=RecipePost.VISIBILITY_FOLLOWERS)
        outsider = User.objects.get(username="@peterpickles")
        try:
            visible = self.service.filter_visible_posts(RecipePost.objects.filter(id=secret.id), outsider)
        except Exception as exc:
            self.fail(str(exc))
        self.assertEqual(list(visible), [])

    def test_is_close_friend_false_when_not_listed(self):
        pal = User.objects.get(username="@peterpickles")
        self.assertFalse(self.service.is_close_friend(pal, self.author))
