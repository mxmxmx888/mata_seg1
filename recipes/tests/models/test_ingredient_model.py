from django.db import IntegrityError
from django.test import TestCase
from recipes.models import User, RecipePost, Ingredient

class IngredientModelTestCase(TestCase):
    fixtures = [
        "recipes/tests/fixtures/default_user.json",
    ]

    def setUp(self):
        author = User.objects.get(username="@johndoe")
        self.post = RecipePost.objects.create(author=author, title="Chili", description="d")

    def test_save_normalises_name_and_str(self):
        ing = Ingredient.objects.create(recipe_post=self.post, name="  ChiliPowder ", position=1, unit="g")
        self.assertEqual(ing.name, "chilipowder")
        self.assertIn("g", str(ing))

    def test_position_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            Ingredient.objects.create(recipe_post=self.post, name="bad", position=0)

    def test_unique_on_position_per_post(self):
        Ingredient.objects.create(recipe_post=self.post, name="salt", position=2)
        with self.assertRaises(IntegrityError):
            Ingredient.objects.create(recipe_post=self.post, name="salt2", position=2)

    def test_blank_name_path_and_str_without_quantity(self):
        ing = Ingredient.objects.create(recipe_post=self.post, name="", position=3, unit="")
        text = str(ing)
        self.assertIn("(", text)
