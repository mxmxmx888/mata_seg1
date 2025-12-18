from django.test import TestCase
from django.urls import reverse

from recipes.tests.helpers import make_recipe_post, make_user
from recipes.views import dashboard_view


class DashboardSearchViewTests(TestCase):
    def setUp(self):
        self.user = make_user(username="searcher")
        self.client.login(username=self.user.username, password="Password123")
        self.url = reverse("dashboard")

    def test_search_matches_title_and_description(self):
        matching = make_recipe_post(
            author=self.user,
            title="Garlic Butter Pasta",
            description="A quick pasta dinner",
        )
        non_matching = make_recipe_post(
            author=self.user,
            title="Tomato Soup",
            description="Cozy soup for winter",
        )

        response = self.client.get(self.url, {"q": "pasta", "mode": "search"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, matching.title)
        self.assertNotContains(response, non_matching.title)

    def test_anonymous_gets_logged_out_discover_page(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/discover_logged_out.html")

    def test_normalise_tags_handles_strings_lists_and_none(self):
        self.assertEqual(dashboard_view._normalise_tags(None), [])
        self.assertEqual(dashboard_view._normalise_tags("A, b ,"), ["a", "b"])
        self.assertEqual(dashboard_view._normalise_tags([" X ", ""]), ["x"])

    def test_filter_posts_by_prep_time_bounds(self):
        class Obj:
            def __init__(self, prep):
                self.prep_time_min = prep

        posts = [Obj(5), Obj(10), Obj(None)]
        self.assertEqual(len(dashboard_view._filter_posts_by_prep_time(posts, 6, None)), 1)
        self.assertEqual(len(dashboard_view._filter_posts_by_prep_time(posts, None, 6)), 1)
