from unittest.mock import patch

from django import forms
from django.test import TestCase
from django.utils.datastructures import MultiValueDict
from django.core.files.uploadedfile import SimpleUploadedFile

from recipes.forms.recipe_forms import RecipePostForm
from recipes.models import User
from recipes.models.ingredient import Ingredient
from recipes.models.recipe_post import RecipePost, RecipeImage


def fake_image(name="img.jpg"):
    return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/jpeg")


class RecipePostFormAdditionalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="@tester",
            email="tester@example.org",
            password="Password123",
        )

    def make_recipe(self):
        return RecipePost.objects.create(
            author=self.user,
            title="T",
            description="D",
            category="Breakfast",
            prep_time_min=1,
            cook_time_min=2,
            nutrition="n",
            visibility=RecipePost.VISIBILITY_PUBLIC,
        )

    def base_form_data(self, **overrides):
        data = {
            "title": "X",
            "description": "Y",
            "category": "dinner",
            "prep_time_min": 1,
            "cook_time_min": 1,
            "nutrition": "",
            "visibility": RecipePost.VISIBILITY_PUBLIC,
        }
        data.update(overrides)
        return data

    def test_parse_tags_handles_empty(self):
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"tags_text": "   ", "category": None}
        self.assertEqual(form.parse_tags(), [])

    def test_parse_shopping_links_returns_empty_when_no_text(self):
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"shopping_links_text": ""}
        self.assertEqual(form._parse_shopping_links(), [])

    def test_parse_shopping_links_skips_blank_lines(self):
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"shopping_links_text": " \nItem | https://example.com"}
        links = form._parse_shopping_links()
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["name"], "Item")

    def test_parse_shopping_links_handles_internal_blank_lines(self):
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"shopping_links_text": "Item1 | http://a.com\n   \nItem2 | b.com"}
        links = form._parse_shopping_links()
        self.assertEqual(len(links), 2)

    def test_parse_shopping_links_skips_blank_name(self):
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"shopping_links_text": " | https://example.com\nItem | example.com"}
        links = form._parse_shopping_links()
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["name"], "Item")
        self.assertEqual(links[0]["url"], "https://example.com")

    def test_create_ingredients_dedupes_lines_and_uses_existing_shop_image(self):
        recipe = self.make_recipe()
        existing_img = fake_image("existing.jpg")
        Ingredient.objects.create(
            recipe_post=recipe,
            name="Existing",
            shop_url="https://old.com",
            shop_image_upload=existing_img,
            position=1,
        )
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {
            "ingredients_text": "Flour\nflour\nSugar",
            "shopping_links_text": "Tea | https://tea.com\nExisting | https://old.com",
            "shop_images": [fake_image("new.jpg")],
        }

        form.create_ingredients(recipe)

        names = list(Ingredient.objects.filter(recipe_post=recipe).order_by("position").values_list("name", flat=True))
        self.assertEqual(names, ["flour", "sugar", "tea", "existing"])
        imgs = list(Ingredient.objects.filter(recipe_post=recipe, shop_url__isnull=False).order_by("position"))
        self.assertTrue(imgs[0].shop_image_upload)
        self.assertTrue(imgs[1].shop_image_upload)

    def test_create_ingredients_skips_blank_lines_and_duplicate_shopping_names(self):
        recipe = self.make_recipe()
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {
            "ingredients_text": "\n\nTomato\n",
            "shopping_links_text": " \nTomato | https://t.com\nTomato | https://duplicate.com",
            "shop_images": [],
        }

        form.create_ingredients(recipe)
        ing_names = list(Ingredient.objects.filter(recipe_post=recipe).values_list("name", flat=True))
        self.assertEqual(ing_names, ["tomato"])

    def test_init_sets_initial_fields_from_instance(self):
        recipe = self.make_recipe()
        Ingredient.objects.create(recipe_post=recipe, name="Carrot", position=1)
        Ingredient.objects.create(recipe_post=recipe, name="Milk", shop_url="https://shop.com/milk", position=2)
        recipe.tags = ["quick", "category:breakfast"]
        recipe.save()
        form = RecipePostForm(instance=recipe)

        self.assertIn("carrot", form.fields["ingredients_text"].initial)
        self.assertIn("milk | https://shop.com/milk", form.fields["shopping_links_text"].initial)
        self.assertIn("quick", form.fields["tags_text"].initial)

    def test_clean_images_called_directly_allows_existing(self):
        recipe = self.make_recipe()
        recipe.image = "legacy.jpg"
        recipe.save()
        form = RecipePostForm(instance=recipe, data={"category": "dinner"}, files=MultiValueDict())
        result = form.clean_images()
        self.assertEqual(result, [])

    def test_clean_images_raises_when_more_than_ten(self):
        files = [fake_image(f"{i}.jpg") for i in range(11)]
        form = RecipePostForm(data={"category": "dinner"}, files=MultiValueDict({"images": files}))
        with self.assertRaises(forms.ValidationError):
            form.clean_images()

    def test_clean_images_with_instance_and_no_existing_raises(self):
        recipe = self.make_recipe()
        form = RecipePostForm(instance=recipe, data={"category": "dinner"}, files=MultiValueDict())
        with self.assertRaises(Exception):
            form.clean_images()

    def test_clean_flags_missing_shop_images(self):
        recipe = self.make_recipe()
        form = RecipePostForm(
            instance=recipe,
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
                "shopping_links_text": "Milk | https://store.com/milk",
            },
            files=MultiValueDict(),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("shop_images", form.errors)

    def test_clean_images_called_directly_checks_existing_db_images(self):
        recipe = self.make_recipe()
        RecipeImage.objects.create(recipe_post=recipe, image=fake_image("old.jpg"), position=0)
        form = RecipePostForm(instance=recipe, data={"category": "dinner"}, files=MultiValueDict())
        self.assertEqual(form.clean_images(), [])

    def test_clean_images_returns_files_for_new_instance(self):
        files = [fake_image("one.jpg")]
        form = RecipePostForm(data={"category": "dinner"}, files=MultiValueDict({"images": files}))
        self.assertEqual(form.clean_images(), files)

    def test_clean_allows_new_instance_with_matching_shop_images(self):
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
                "shopping_links_text": "Salt | https://shop.com/salt",
            },
            files=MultiValueDict({"images": [fake_image("cover.jpg")], "shop_images": [fake_image("salt.jpg")]}),
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_clean_counts_existing_shop_images_direct_call(self):
        recipe = self.make_recipe()
        Ingredient.objects.create(
            recipe_post=recipe,
            name="Milk",
            shop_url="https://shop.com/milk",
            shop_image_upload=fake_image("keep.jpg"),
            position=1,
        )
        form = RecipePostForm(
            data=self.base_form_data(shopping_links_text="Milk | https://shop.com/milk"),
            instance=recipe,
            files=MultiValueDict({"images": [fake_image("cover.jpg")]}),
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.clean().get("title"), "X")

    def test_create_ingredients_skips_blank_items_when_overridden(self):
        recipe = self.make_recipe()
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"shop_images": [], "shopping_links_text": "", "ingredients_text": ""}
        form._split_lines = lambda key: ["", "Egg"]
        form._parse_shopping_links = lambda: [{"name": "   ", "url": None}]
        form.create_ingredients(recipe)
        names = list(Ingredient.objects.filter(recipe_post=recipe).values_list("name", flat=True))
        self.assertEqual(names, ["egg"])

    def test_clean_handles_zero_shopping_links(self):
        recipe = self.make_recipe()
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
                "shopping_links_text": "",
            },
            instance=recipe,
            files=MultiValueDict({"images": [fake_image("cover.jpg")]}),
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_init_handles_missing_nutrition_field(self):
        fields_without_nutrition = {
            name: field for name, field in RecipePostForm.base_fields.items() if name != "nutrition"
        }
        with patch.object(RecipePostForm, "base_fields", fields_without_nutrition):
            form = RecipePostForm()
            self.assertNotIn("nutrition", form.fields)
