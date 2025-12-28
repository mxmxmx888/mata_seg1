from types import SimpleNamespace

from django.test import RequestFactory, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from recipes.models import Favourite, FavouriteItem, User
from recipes.models.recipe_post import RecipePost, RecipeImage
from recipes.views import recipe_view_helpers as helpers


class RecipeViewHelpersTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="@helper",
            email="h@example.com",
            password="Password123",
        )
        self.recipe = RecipePost.objects.create(
            author=self.user,
            title="T",
            description="D",
            category="dinner",
            prep_time_min=1,
            cook_time_min=1,
        )

    def test_collection_thumb_uses_placeholder_when_missing(self):
        url = helpers.collection_thumb(None, None)
        self.assertIn("placehold.co", url)

    def test_primary_image_url_handles_value_error_and_fallbacks(self):
        class BadImage:
            @property
            def url(self):
                raise ValueError()

        class Images(list):
            def first(self):
                return self[0] if self else None

        recipe = SimpleNamespace(image="fallback.jpg", images=Images([SimpleNamespace(image=BadImage())]))
        self.assertEqual(helpers.primary_image_url(recipe), "fallback.jpg")

    def test_resolve_collection_creates_default_when_missing(self):
        request = self.factory.post("/", {})
        request.user = self.user

        favourite, created = helpers.resolve_collection(request, self.recipe)

        self.assertTrue(created)
        self.assertEqual(favourite.name, "favourites")

    def test_is_hx_handles_xmlhttprequest_header_and_defaults_false(self):
        req = self.factory.get("/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(helpers.is_hx(req))
        self.assertFalse(helpers.is_hx(self.factory.get("/")))

    def test_set_primary_image_persists_first_image_url(self):
        img = SimpleUploadedFile("p.jpg", b"abc", content_type="image/jpeg")
        RecipeImage.objects.create(recipe_post=self.recipe, image=img, position=0)

        helpers.set_primary_image(self.recipe)
        self.recipe.refresh_from_db()

        self.assertIn("p.jpg", self.recipe.image)

    def test_toggle_save_creates_and_removes_items(self):
        fav = Favourite.objects.create(user=self.user, name="Mine")
        saved, count = helpers.toggle_save(fav, self.recipe)
        self.assertTrue(saved)
        self.assertEqual(count, 1)
        self.assertTrue(FavouriteItem.objects.filter(favourite=fav, recipe_post=self.recipe).exists())

        saved_again, new_count = helpers.toggle_save(fav, self.recipe)
        self.assertFalse(saved_again)
        self.assertEqual(new_count, 0)
