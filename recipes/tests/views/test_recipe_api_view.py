from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from recipes.models import User, Recipe


class RecipeApiViewTestCase(TestCase):
    fixtures = [
        'recipes/tests/fixtures/default_user.json',
        'recipes/tests/fixtures/other_users.json',
    ]

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.get(username='@johndoe')
        self.other_user = User.objects.exclude(pk=self.user.pk).first()
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
            "ingredients": "pasta, garlic, butter",
            "category": "pasta",
            "cook_time_minutes": 15,
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Recipe.objects.count(), 1)
        recipe = Recipe.objects.first()
        self.assertEqual(recipe.owner, self.user)
        self.assertEqual(recipe.title, "Simple pasta")

    def test_list_can_filter_by_search(self):
        Recipe.objects.create(
            owner=self.user,
            title="Garlic butter pasta",
            description="garlic and butter",
            ingredients_text="pasta, garlic, butter",
            category="pasta",
        )
        Recipe.objects.create(
            owner=self.user,
            title="Tomato soup",
            description="tomato and basil",
            ingredients_text="tomato, basil, stock",
            category="soup",
        )

        response = self.client.get(self.list_url + "?search=pasta")
        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.json()]
        self.assertIn("Garlic butter pasta", titles)
        self.assertNotIn("Tomato soup", titles)

    def test_list_can_filter_by_ingredient_and_category(self):
        Recipe.objects.create(
            owner=self.user,
            title="Lemon chicken pasta",
            ingredients_text="pasta, chicken, lemon",
            category="pasta",
        )
        Recipe.objects.create(
            owner=self.user,
            title="Plain pasta",
            ingredients_text="pasta, salt",
            category="pasta",
        )
        Recipe.objects.create(
            owner=self.user,
            title="Chicken salad",
            ingredients_text="chicken, lettuce",
            category="salad",
        )

        url = self.list_url + "?ingredient=chicken&category=pasta"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.json()]
        self.assertIn("Lemon chicken pasta", titles)
        self.assertNotIn("Plain pasta", titles)
        self.assertNotIn("Chicken salad", titles)

    def test_sorting_by_rating(self):
        low = Recipe.objects.create(
            owner=self.user,
            title="Average pasta",
            ingredients_text="pasta",
            category="pasta",
            average_rating=3.0,
            ratings_count=2,
        )
        high = Recipe.objects.create(
            owner=self.user,
            title="Top pasta",
            ingredients_text="pasta",
            category="pasta",
            average_rating=4.8,
            ratings_count=10,
        )

        response = self.client.get(self.list_url + "?ordering=rating")
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.json()]
        self.assertEqual(ids[0], high.id)
        self.assertIn(low.id, ids)

    def test_owner_can_update_recipe(self):
        recipe = Recipe.objects.create(
            owner=self.user,
            title="Old title",
            ingredients_text="pasta",
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
        recipe = Recipe.objects.create(
            owner=self.user,
            title="Protected",
            ingredients_text="pasta",
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
        recipe = Recipe.objects.create(
            owner=self.user,
            title="To delete",
            ingredients_text="pasta",
            category="pasta",
        )
        url = reverse('recipe_detail_api', kwargs={"pk": recipe.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Recipe.objects.filter(pk=recipe.pk).exists())
