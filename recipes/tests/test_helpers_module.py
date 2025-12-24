from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from recipes.models import User
from recipes.models.recipe_post import RecipePost
from recipes.tests import test_utils as helpers


class ReverseWithNextTests(SimpleTestCase):
    def test_appends_next_querystring(self):
        base = reverse("dashboard")
        out = helpers.reverse_with_next("dashboard", "/profile/")
        self.assertEqual(out, f"{base}?next=/profile/")


class MakeUserTests(TestCase):
    def test_creates_user_with_defaults(self):
        user = helpers.make_user()

        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertTrue(user.username.startswith("@"))
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.bio, "Test bio")
        self.assertTrue(user.check_password("Password123"))

    def test_prefixes_username_and_respects_overrides(self):
        user = helpers.make_user(
            username="alice",
            first_name="Alice",
            last_name="Wonder",
            bio="Custom bio",
            password="Secret123",
        )

        self.assertEqual(user.username, "@alice")
        self.assertTrue(user.email.startswith("alice_"))
        self.assertEqual(user.first_name, "Alice")
        self.assertEqual(user.last_name, "Wonder")
        self.assertEqual(user.bio, "Custom bio")
        self.assertTrue(user.check_password("Secret123"))


class MakeRecipePostTests(TestCase):
    def test_creates_post_with_generated_author_and_published_at(self):
        post = helpers.make_recipe_post()

        self.assertIsInstance(post.author, User)
        self.assertEqual(post.title, "test post")
        self.assertEqual(post.description, "desc")
        self.assertIsNotNone(post.published_at)

    def test_accepts_explicit_author_and_respects_published_flag(self):
        author = helpers.make_user(username="@poster")
        post = helpers.make_recipe_post(author=author, title="Draft", published=False)

        self.assertEqual(post.author, author)
        self.assertEqual(post.title, "Draft")
        self.assertIsNone(post.published_at)


class LogInTesterTests(helpers.LogInTester, TestCase):
    def test_is_logged_in_reflects_session_state(self):
        self.assertFalse(self._is_logged_in())

        user = helpers.make_user()
        self.client.force_login(user)
        self.assertTrue(self._is_logged_in())


class MenuTesterMixinTests(helpers.MenuTesterMixin, SimpleTestCase):
    def _response_with_links(self, urls):
        html = "".join(f'<a href="{url}">link</a>' for url in urls)
        return HttpResponse(html)

    def test_assert_menu_checks_all_menu_links(self):
        response = self._response_with_links(self.get_menu_urls())
        self.assert_menu(response)

    def test_assert_no_menu_checks_absence_of_links(self):
        response = HttpResponse("<p>No menu links here</p>")
        self.assert_no_menu(response)
