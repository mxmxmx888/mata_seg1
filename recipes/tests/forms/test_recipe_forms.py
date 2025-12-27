from django.test import TestCase
from django.utils.datastructures import MultiValueDict

from recipes.forms.recipe_forms import (
    MAX_SHOPPING_LINKS,
    RecipePostForm,
)
from recipes.models import User
from recipes.models.recipe_post import RecipePost, RecipeImage
from recipes.models.recipe_step import RecipeStep
from recipes.models.ingredient import Ingredient
from recipes.tests.forms.form_file_helpers import fake_image, oversized_image


class RecipePostFormTests(TestCase):
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

    def test_parse_tags_adds_category_tag(self):
        form = RecipePostForm(
            data={
                "title": "Pasta",
                "description": "Nice",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
                "tags_text": "quick, ,  family ",
            }
            ,
            files=MultiValueDict({"images": [fake_image("cover.jpg")]}),
        )
        self.assertTrue(form.is_valid(), form.errors)
        tags = form.parse_tags()
        self.assertIn("quick", tags)
        self.assertIn("family", tags)
        self.assertIn("category:dinner", tags)

    def test_serves_rejects_non_numeric_input(self):
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "serves": "abc",
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
            },
            files=MultiValueDict({"images": [fake_image("cover.jpg")]}),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("whole number", str(form.errors["serves"]))

    def test_split_lines_strips_and_ignores_blanks(self):
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"ingredients_text": "  a \n\n b \n   \n"}
        self.assertEqual(form._split_lines("ingredients_text"), ["a", "b"])

    def test_split_lines_returns_empty_when_blank(self):
        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"ingredients_text": "   "}
        self.assertEqual(form._split_lines("ingredients_text"), [])

    def test_create_steps_replaces_existing(self):
        recipe = self.make_recipe()
        RecipeStep.objects.create(recipe_post=recipe, position=1, description="old")

        form = RecipePostForm(data={"category": "dinner"})
        form.cleaned_data = {"steps_text": "step 1\nstep 2"}
        form.create_steps(recipe)

        steps = list(RecipeStep.objects.filter(recipe_post=recipe).order_by("position"))
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].position, 1)
        self.assertEqual(steps[0].description, "step 1")
        self.assertEqual(steps[1].position, 2)
        self.assertEqual(steps[1].description, "step 2")

    def test_create_images_replaces_existing_and_caps_at_10(self):
        recipe = self.make_recipe()
        RecipeImage.objects.create(recipe_post=recipe, image=fake_image("old.jpg"), position=0)

        files = [fake_image(f"{i}.jpg") for i in range(12)]
        form = RecipePostForm(data={"category": "dinner"}, files=MultiValueDict({"images": files}))

        form.create_images(recipe)

        imgs = list(RecipeImage.objects.filter(recipe_post=recipe).order_by("position"))
        self.assertEqual(len(imgs), 10)  # capped
        self.assertEqual(imgs[0].position, 0)
        self.assertEqual(imgs[9].position, 9)

    def test_create_images_keeps_existing_when_no_new_files(self):
        recipe = self.make_recipe()
        existing = RecipeImage.objects.create(recipe_post=recipe, image=fake_image("keep.jpg"), position=0)

        form = RecipePostForm(data={"category": "dinner"}, files=MultiValueDict())

        form.create_images(recipe)

        imgs = list(RecipeImage.objects.filter(recipe_post=recipe).order_by("position"))
        self.assertEqual(len(imgs), 1)
        self.assertIn("keep", imgs[0].image.name)
        self.assertEqual(imgs[0].position, 0)

    def test_create_ingredients_replaces_existing_dedupes_and_parses_shop_url(self):
        recipe = self.make_recipe()
        Ingredient.objects.create(recipe_post=recipe, name="old", position=1)

        # Manual ingredient list (no shopping links here)
        ingredients_text = "Flour"

        # Shopping links:
        # 1st has url without scheme -> should become https://...
        # 2nd is dup (case-insensitive) -> skipped
        # 3rd has https url -> should be stored as-is and consume the 2nd shop image
        # 4th has no url -> url stays None (and should not consume a shop_image)
        shopping_links_text = "\n".join([
            "Matcha Powder | amazon.com/matcha",
            "  matcha powder  | https://example.com/dup ",
            "Milk | https://store.com/milk",
            "Plate",
        ])

        shop_imgs = [fake_image("s1.jpg"), fake_image("s2.jpg")]
        form = RecipePostForm(data={"category": "dinner"}, files=MultiValueDict({"shop_images": shop_imgs}))
        form.cleaned_data = {
            "ingredients_text": ingredients_text,
            "shopping_links_text": shopping_links_text,
            "shop_images": shop_imgs,
        }

        form.create_ingredients(recipe)

        ings = list(Ingredient.objects.filter(recipe_post=recipe).order_by("position"))
        self.assertEqual(len(ings), 4)  # dup removed, old removed

        self.assertEqual(ings[0].name, "flour")
        self.assertIsNone(ings[0].shop_url)
        self.assertFalse(bool(ings[0].shop_image_upload))

        self.assertEqual(ings[1].name, "matcha powder")
        self.assertEqual(ings[1].shop_url, "https://amazon.com/matcha")
        self.assertTrue(bool(ings[1].shop_image_upload))  # consumed s1

        self.assertEqual(ings[2].name, "milk")
        self.assertEqual(ings[2].shop_url, "https://store.com/milk")
        self.assertTrue(bool(ings[2].shop_image_upload))  # consumed s2

        self.assertEqual(ings[3].name, "plate")
        self.assertIsNone(ings[3].shop_url)
        self.assertFalse(bool(ings[3].shop_image_upload))

    def test_clean_images_limits_to_10(self):
        files = [fake_image(f"{i}.jpg") for i in range(11)]
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
            },
            files=MultiValueDict({"images": files}),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)
        self.assertIn("up to 10 images", str(form.errors["images"]))

    def test_clean_images_rejects_files_over_size_limit(self):
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
            },
            files=MultiValueDict({"images": [oversized_image()]}),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)
        self.assertIn("MB or smaller", str(form.errors["images"]))
        self.assertIn("big.jpg", str(form.errors["images"]))

    def test_clean_shop_images_limits_to_10(self):
        files = [fake_image(f"{i}.jpg") for i in range(11)]
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
            },
            files=MultiValueDict({"shop_images": files}),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("shop_images", form.errors)
        self.assertIn("up to 10 shopping images", str(form.errors["shop_images"]))

    def test_clean_shop_images_rejects_files_over_size_limit(self):
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
            },
            files=MultiValueDict(
                {
                    "images": [fake_image("cover.jpg")],
                    "shop_images": [oversized_image("too-big.jpg")],
                }
            ),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("shop_images", form.errors)
        self.assertIn("MB or smaller", str(form.errors["shop_images"]))
        self.assertIn("too-big.jpg", str(form.errors["shop_images"]))

    def test_clean_images_requires_one_on_create(self):
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
            },
            files=MultiValueDict(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("images", form.errors)
        self.assertIn("at least one image", str(form.errors["images"]))

    def test_clean_images_allows_existing_on_edit(self):
        recipe = self.make_recipe()
        RecipeImage.objects.create(recipe_post=recipe, image=fake_image("existing.jpg"), position=0)

        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
            },
            instance=recipe,
            files=MultiValueDict(),
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_clean_images_allows_existing_legacy_image(self):
        recipe = self.make_recipe()
        recipe.image = "legacy.jpg"
        recipe.save()

        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
            },
            instance=recipe,
            files=MultiValueDict(),
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_clean_requires_shop_images_for_each_link(self):
        files = MultiValueDict({"shop_images": [fake_image("only1.jpg")]})
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
                "shopping_links_text": "Milk | https://store.com/milk\nFlour | amazon.com/flour",
            },
            files=files,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("shop_images", form.errors)
        self.assertIn("need 2, provided 1", str(form.errors["shop_images"]))

    def test_clean_enforces_max_shopping_links(self):
        too_many_links = "\n".join(
            f"Item{i} | example{i}.com" for i in range(MAX_SHOPPING_LINKS + 1)
        )
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
                "shopping_links_text": too_many_links,
            },
            files=MultiValueDict({"images": [fake_image("cover.jpg")]}),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("shopping_links_text", form.errors)
        self.assertIn("Add up to", str(form.errors["shopping_links_text"]))

    def test_clean_accepts_enough_shop_images_for_links(self):
        files = MultiValueDict({
            "shop_images": [fake_image("milk.jpg"), fake_image("flour.jpg")],
        })
        form = RecipePostForm(
            data={
                "title": "X",
                "description": "Y",
                "category": "dinner",
                "prep_time_min": 1,
                "cook_time_min": 1,
                "nutrition": "",
                "visibility": RecipePost.VISIBILITY_PUBLIC,
                "shopping_links_text": "Milk | https://store.com/milk\nFlour | amazon.com/flour",
            },
            files=MultiValueDict({
                "shop_images": [fake_image("milk.jpg"), fake_image("flour.jpg")],
                "images": [fake_image("cover.jpg")],
            }),
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_clean_counts_existing_shop_images(self):
        recipe = self.make_recipe()
        Ingredient.objects.create(
            recipe_post=recipe,
            name="Milk",
            shop_url="https://store.com/milk",
            shop_image_upload=fake_image("existing.jpg"),
            position=1,
        )
        form = RecipePostForm(
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
            instance=recipe,
            files=MultiValueDict({"images": [fake_image("cover.jpg")]}),
        )

        self.assertTrue(form.is_valid(), form.errors)
