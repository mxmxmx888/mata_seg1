from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory

from recipes.models.favourite import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.models.recipe_post import RecipePost, RecipeImage
from recipes.tests.views.base import RecipeViewTestCase, add_session_and_messages
import recipes.views.recipe_views as recipe_views
from recipes.views.recipe_views import recipe_create, recipe_detail, recipe_edit
from recipes.views.recipe_view_helpers import hx_response_or_redirect


class RecipeViewsCreateEditTests(RecipeViewTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.default_form_data = {
            "title": "Title",
            "description": "Desc",
            "prep_time_min": 1,
            "cook_time_min": 1,
            "nutrition": "",
            "category": "",
            "visibility": RecipePost.VISIBILITY_PUBLIC,
        }

    def _mock_form(self, MockForm, data=None, tags=None, image_hook=None):
        form = MagicMock()
        payload = dict(self.default_form_data)
        payload.update(data or {})
        form.cleaned_data = payload
        form.is_valid.return_value = True
        form.parse_tags.return_value = tags or []
        form.create_ingredients.side_effect = lambda recipe: None
        form.create_steps.side_effect = lambda recipe: None
        form.create_images.side_effect = image_hook or (lambda recipe: None)
        MockForm.return_value = form
        return form

    def test_recipe_create_requires_login(self):
        request = self.factory.get("/fake/recipe/create/")
        request.user = AnonymousUser()
        add_session_and_messages(request)

        response = recipe_create(request)
        self.assertEqual(response.status_code, 302)

    def test_recipe_detail_requires_login(self):
        request = self.factory.get(f"/fake/recipe/{self.post.id}/")
        request.user = AnonymousUser()
        add_session_and_messages(request)

        response = recipe_detail(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)

    @patch("recipes.views.recipe_views.RecipePostForm")
    def test_recipe_create_post_valid_creates_recipe_and_redirects(self, MockForm):
        self._mock_form(
            MockForm,
            data={
                "title": "Created title",
                "description": "Created desc",
                "prep_time_min": 3,
                "cook_time_min": 7,
                "nutrition": "kcal=500",
                "category": "Lunch",
            },
            tags=["tag1", "tag2"],
        )
        request = self.factory.post("/fake/recipe/create/", data={"title": "x"})
        request.user = self.user
        add_session_and_messages(request)
        with patch("recipes.views.recipe_views.PrivacyService.can_view_post", return_value=True):
            response = recipe_create(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            RecipePost.objects.filter(title="Created title", author=self.user).exists()
        )

    def test_recipe_create_get_renders_form(self):
        request = self.factory.get("/fake/recipe/create/")
        request.user = self.user
        add_session_and_messages(request)

        response = recipe_create(request)
        self.assertEqual(response.status_code, 200)

    @patch("recipes.views.recipe_views.RecipePostForm")
    def test_recipe_create_sets_primary_image_when_present(self, MockForm):
        def set_image(recipe):
            image_file = SimpleUploadedFile(
                "test.jpg", b"abc", content_type="image/jpeg"
            )
            RecipeImage.objects.create(recipe_post=recipe, image=image_file, position=0)

        self._mock_form(
            MockForm,
            data={"title": "With image", "prep_time_min": 0, "cook_time_min": 0},
            image_hook=set_image,
        )

        request = self.factory.post("/fake/recipe/create/", data={"title": "With image"})
        request.user = self.user
        add_session_and_messages(request)

        response = recipe_create(request)
        self.assertEqual(response.status_code, 302)
        post = RecipePost.objects.get(title="With image")
        self.assertIn("test", post.image)

    def test_recipe_edit_non_author_gets_404(self):
        request = self.factory.get(f"/fake/recipe/{self.post.id}/edit/")
        request.user = self.other
        add_session_and_messages(request)

        with self.assertRaises(Http404):
            recipe_edit(request, post_id=self.post.id)

    @patch("recipes.views.recipe_views.RecipePostForm")
    def test_recipe_edit_post_valid_updates_recipe(self, MockForm):
        self._mock_form(
            MockForm,
            data={
                "title": "Updated",
                "description": "Updated desc",
                "prep_time_min": 11,
                "cook_time_min": 22,
                "nutrition": "kcal=700",
                "category": "Breakfast",
            },
            tags=["newtag"],
        )
        request = self.factory.post(
            f"/fake/recipe/{self.post.id}/edit/", data={"title": "Updated"}
        )
        request.user = self.user
        add_session_and_messages(request)
        response = recipe_edit(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Updated")
        self.assertEqual(self.post.prep_time_min, 11)
        self.assertEqual(self.post.cook_time_min, 22)

    def test_recipe_edit_get_returns_form(self):
        request = self.factory.get(f"/fake/recipe/{self.post.id}/edit/")
        request.user = self.user
        add_session_and_messages(request)

        response = recipe_edit(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 200)

    @patch("recipes.views.recipe_views.RecipePostForm")
    def test_recipe_edit_updates_primary_image_when_present(self, MockForm):
        def set_image(recipe):
            image_file = SimpleUploadedFile(
                "updated.jpg", b"123", content_type="image/jpeg"
            )
            RecipeImage.objects.create(recipe_post=recipe, image=image_file, position=0)

        self._mock_form(
            MockForm,
            data={"title": "Updated", "prep_time_min": 1, "cook_time_min": 2},
            image_hook=set_image,
        )

        request = self.factory.post(
            f"/fake/recipe/{self.post.id}/edit/", data={"title": "Updated"}
        )
        request.user = self.user
        add_session_and_messages(request)

        response = recipe_edit(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertIn("updated", self.post.image)

    def test_is_hx_helper(self):
        req = self.factory.get("/hx", HTTP_HX_REQUEST="true")
        self.assertTrue(recipe_views._is_hx(req))

        req2 = self.factory.get("/hx", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(recipe_views._is_hx(req2))

        req3 = self.factory.get("/hx")
        self.assertFalse(recipe_views._is_hx(req3))

    def test_primary_image_and_gallery_helpers(self):
        class BadUrl:
            @property
            def url(self):
                raise ValueError()

        class Images:
            def __init__(self, first_obj):
                self._first = first_obj

            def first(self):
                return self._first

        recipe = SimpleNamespace(
            image="fallback.jpg", images=Images(SimpleNamespace(image=BadUrl()))
        )
        self.assertEqual(recipe_views._primary_image_url(recipe), "fallback.jpg")

        first = SimpleNamespace(image=SimpleNamespace(url="first.jpg"))
        second = SimpleNamespace(image=SimpleNamespace(url="second.jpg"))
        bad = SimpleNamespace(image=BadUrl())
        gallery = recipe_views._gallery_images([first, second, bad])
        self.assertEqual(gallery, ["second.jpg"])

    def test_hx_response_or_redirect_covers_both_branches(self):
        hx_request = self.factory.get("/hx", HTTP_HX_REQUEST="true")
        resp = hx_response_or_redirect(hx_request, "/target")
        self.assertEqual(resp.status_code, 204)

        normal_request = self.factory.get("/hx")
        resp2 = hx_response_or_redirect(normal_request, "/target")
        self.assertEqual(resp2.status_code, 302)
        self.assertEqual(resp2.url, "/target")

    def test_collections_modal_state_sorts_saved_first(self):
        self.post.image = "cover.jpg"
        self.post.save(update_fields=["image"])
        other_post = RecipePost.objects.create(
            author=self.user, title="Another", description="Other",
            prep_time_min=1, cook_time_min=1, tags=["other"],
            category="Lunch", visibility=RecipePost.VISIBILITY_PUBLIC,
        )
        fav_saved = Favourite.objects.create(user=self.user, name="A")
        fav_other = Favourite.objects.create(user=self.user, name="B")
        saved_item = FavouriteItem.objects.create(favourite=fav_saved, recipe_post=self.post)
        FavouriteItem.objects.create(
            favourite=fav_other,
            recipe_post=other_post,
            added_at=saved_item.added_at - timedelta(hours=1),
        )

        collections = recipe_views._collections_modal_state(self.user, self.post)
        self.assertEqual(collections[0]["id"], str(fav_saved.id))
        self.assertTrue(collections[0]["saved"])
        self.assertFalse(collections[1]["saved"])
        self.assertEqual(collections[0]["thumb_url"], "cover.jpg")
