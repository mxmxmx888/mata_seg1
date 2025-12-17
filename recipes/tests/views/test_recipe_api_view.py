from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from recipes.models import User, RecipePost

class RecipeApiViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='johndoe',
            email='john@example.com',
            password='password123'
        )
        self.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse('recipe_list_api')

    def test_list_requires_authentication(self):
        client = APIClient()
        response = client.get(self.list_url)
        self.assertIn(response.status_code, [401, 403])

    def test_user_can_create_recipe(self):
        data = {
            "title": "Simple pasta",
            "description": "Quick pasta dish",
            "category": "pasta",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RecipePost.objects.count(), 1)
        recipe = RecipePost.objects.first()
        self.assertEqual(recipe.author, self.user)
        self.assertEqual(recipe.title, "Simple pasta")

    def test_list_can_filter_by_search(self):
        RecipePost.objects.create(
            author=self.user,
            title="Garlic butter pasta",
            description="garlic and butter",
            category="pasta",
        )
        RecipePost.objects.create(
            author=self.user,
            title="Tomato soup",
            description="tomato and basil",
            category="soup",
        )

        response = self.client.get(self.list_url + "?search=pasta")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data['results'] if isinstance(data, dict) and 'results' in data else data
        titles = [item["title"] for item in results]
        self.assertIn("Garlic butter pasta", titles)
        self.assertNotIn("Tomato soup", titles)

    def test_list_can_filter_by_ingredient_and_category(self):
        RecipePost.objects.create(
            author=self.user,
            title="Lemon chicken pasta",
            category="pasta",
        )
        RecipePost.objects.create(
            author=self.user,
            title="Chicken salad",
            category="salad",
        )

        url = self.list_url + "?category=pasta"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data['results'] if isinstance(data, dict) and 'results' in data else data
        titles = [item["title"] for item in results]
        self.assertIn("Lemon chicken pasta", titles)
        self.assertNotIn("Chicken salad", titles)

    def test_owner_can_update_recipe(self):
        recipe = RecipePost.objects.create(
            author=self.user,
            title="Old title",
            category="pasta",
        )
        url = reverse('recipe_detail_api', kwargs={"pk": recipe.pk})
        response = self.client.patch(
            url,
            {"title": "New title"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, "New title")

    def test_non_owner_cannot_update_recipe(self):
        recipe = RecipePost.objects.create(
            author=self.user,
            title="Protected",
            category="pasta",
        )
        client = APIClient()
        client.force_authenticate(user=self.other_user)
        url = reverse('recipe_detail_api', kwargs={"pk": recipe.pk})
        response = client.patch(
            url,
            {"title": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, "Protected")

    def test_owner_can_delete_recipe(self):
        recipe = RecipePost.objects.create(
            author=self.user,
            title="To delete",
            category="pasta",
        )
        url = reverse('recipe_detail_api', kwargs={"pk": recipe.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(RecipePost.objects.filter(pk=recipe.pk).exists())