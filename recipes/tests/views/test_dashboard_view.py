from django.test import TestCase
from django.urls import reverse

from recipes.tests.helpers import make_recipe_post, make_user


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
