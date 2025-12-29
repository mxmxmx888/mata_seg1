from types import SimpleNamespace
from datetime import timedelta

from django.test import RequestFactory, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from unittest.mock import patch

from recipes.models import Favourite, FavouriteItem, User, Ingredient
from recipes.models.followers import Follower
from recipes.models.like import Like
from recipes.models.recipe_post import RecipePost, RecipeImage
from recipes.models.recipe_step import RecipeStep
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

    def test_is_hx_handles_headers_and_defaults_false(self):
        self.assertTrue(helpers.is_hx(self.factory.get("/", HTTP_HX_REQUEST="true")))
        self.assertTrue(helpers.is_hx(self.factory.get("/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")))
        self.assertFalse(helpers.is_hx(self.factory.get("/")))

    def test_set_primary_image_persists_first_image_url(self):
        img = SimpleUploadedFile("p.jpg", b"abc", content_type="image/jpeg")
        RecipeImage.objects.create(recipe_post=self.recipe, image=img, position=0)

        helpers.set_primary_image(self.recipe)
        self.recipe.refresh_from_db()

        self.assertTrue(self.recipe.image.endswith(".jpg"))

    def test_set_primary_image_no_images_leaves_image_empty(self):
        helpers.set_primary_image(self.recipe)
        self.recipe.refresh_from_db()
        self.assertFalse(self.recipe.image)

    def test_collection_thumb_prefers_cover_primary_then_fallback_or_placeholder(self):
        cover = SimpleNamespace(primary_image_url="cover.png", image=None)
        fallback = SimpleNamespace(primary_image_url=None, image="fallback.png")
        self.assertEqual(helpers.collection_thumb(cover, fallback), "cover.png")
        self.assertEqual(helpers.collection_thumb(None, fallback), "fallback.png")
        self.assertIn("placehold.co", helpers.collection_thumb(None, None))

    def test_user_reactions_reports_flags_and_counts(self):
        author = User.objects.create_user(username="@author", email="a@example.com", password="Password123")
        self.recipe.author = author
        self.recipe.save(update_fields=["author"])
        fav = Favourite.objects.create(user=self.user, name="Mine")
        Like.objects.create(user=self.user, recipe_post=self.recipe)
        FavouriteItem.objects.create(favourite=fav, recipe_post=self.recipe)
        Follower.objects.create(follower=self.user, author=author)

        reactions = helpers.user_reactions(self.user, self.recipe)

        self.assertTrue(reactions["user_liked"])
        self.assertTrue(reactions["user_saved"])
        self.assertTrue(reactions["is_following_author"])
        self.assertEqual(reactions["likes_count"], 1)
        self.assertEqual(reactions["saves_count"], 1)

    def test_recipe_media_returns_gallery(self):
        img1 = RecipeImage.objects.create(recipe_post=self.recipe, image=SimpleUploadedFile("a.jpg", b"a"), position=0)
        RecipeImage.objects.create(recipe_post=self.recipe, image=SimpleUploadedFile("b.jpg", b"b"), position=1)

        image_url, gallery = helpers.recipe_media(self.recipe)

        self.assertTrue(image_url.endswith(".jpg"))
        self.assertTrue(any(g.endswith(".jpg") for g in gallery))

    def test_primary_image_url_returns_legacy_when_no_gallery(self):
        self.recipe.image = "legacy.jpg"
        self.recipe.save(update_fields=["image"])
        url = helpers.primary_image_url(self.recipe)
        self.assertEqual(url, "legacy.jpg")

    def test_collections_modal_state_marks_saved_first(self):
        fav_saved = Favourite.objects.create(user=self.user, name="Saved")
        fav_other = Favourite.objects.create(user=self.user, name="Other")
        FavouriteItem.objects.create(favourite=fav_saved, recipe_post=self.recipe)
        other_post = RecipePost.objects.create(
            author=self.user,
            title="Other",
            description="d",
            category="dinner",
            prep_time_min=1,
            cook_time_min=1,
        )
        FavouriteItem.objects.create(favourite=fav_other, recipe_post=other_post)

        collections = helpers.collections_modal_state(self.user, self.recipe)

        self.assertEqual(collections[0]["id"], str(fav_saved.id))
        self.assertTrue(collections[0]["saved"])
        self.assertEqual(collections[0]["count"], 1)

    def test_collections_modal_state_updates_last_saved_and_cover(self):
        fav = Favourite.objects.create(user=self.user, name="X")
        RecipeImage.objects.create(recipe_post=self.recipe, image=SimpleUploadedFile("c.jpg", b"c"), position=0)
        item = FavouriteItem.objects.create(favourite=fav, recipe_post=self.recipe)
        FavouriteItem.objects.filter(id=item.id).update(added_at=fav.created_at + timezone.timedelta(hours=1))

        result = helpers.collections_modal_state(self.user, self.recipe)[0]

        self.assertTrue(result["last_saved_at"] > fav.created_at)
        self.assertTrue(result["thumb_url"])

    @patch("recipes.views.recipe_view_helpers.Favourite.objects.filter")
    def test_collections_modal_state_updates_last_saved_and_cover_for_unsaved(self, mock_filter):
        added_at = timezone.now()
        item = SimpleNamespace(
            recipe_post_id=999,
            recipe_post=SimpleNamespace(primary_image_url="fromitem", image=None),
            added_at=added_at,
        )
        class FakeQS(list):
            def prefetch_related(self, *args, **kwargs):
                return self
        fav = SimpleNamespace(
            id="fake",
            name="Fake",
            created_at=added_at - timedelta(hours=1),
            cover_post=None,
            items=SimpleNamespace(all=lambda: [item]),
        )
        mock_filter.return_value = FakeQS([fav])

        result = helpers.collections_modal_state(self.user, self.recipe)[0]

        self.assertEqual(result["last_saved_at"], added_at)
        self.assertEqual(result["thumb_url"], "fromitem")

    @patch("recipes.views.recipe_view_helpers.Favourite.objects.filter")
    def test_collections_modal_state_handles_missing_added_at(self, mock_filter):
        class FakeQS(list):
            def prefetch_related(self, *args, **kwargs):
                return self
        fav = SimpleNamespace(
            id="fav",
            name="Fav",
            created_at=timezone.now(),
            cover_post=SimpleNamespace(primary_image_url="cover", image=None),
            items=SimpleNamespace(
                all=lambda: [
                    SimpleNamespace(
                        recipe_post_id=self.recipe.id,
                        recipe_post=None,
                        added_at=None,
                    )
                ]
            ),
        )
        mock_filter.return_value = FakeQS([fav])
        result = helpers.collections_modal_state(self.user, self.recipe)[0]
        self.assertEqual(result["last_saved_at"], fav.created_at)
        self.assertEqual(result["thumb_url"], "cover")

    def test_gallery_images_skips_value_error(self):
        class Bad:
            @property
            def url(self):
                raise ValueError()
        images = [SimpleNamespace(image=SimpleNamespace(url="ok")), SimpleNamespace(image=Bad())]

        gallery = helpers.gallery_images(images)

        self.assertEqual(gallery, [])

    def test_recipe_media_single_image_has_empty_gallery(self):
        RecipeImage.objects.create(recipe_post=self.recipe, image=SimpleUploadedFile("only.jpg", b"x"), position=0)
        image_url, gallery = helpers.recipe_media(self.recipe)
        self.assertTrue(image_url.endswith(".jpg"))
        self.assertEqual(gallery, [])

    def test_first_item_post_and_last_saved_defaults(self):
        self.assertIsNone(helpers._first_item_post([]))
        now = timezone.now()
        self.assertEqual(helpers._last_saved_at([], now), now)

    def test_first_item_post_returns_first_available(self):
        items = [SimpleNamespace(recipe_post=self.recipe)]

        self.assertEqual(helpers._first_item_post(items), self.recipe)

    def test_first_item_post_skips_missing_posts(self):
        items = [SimpleNamespace(recipe_post=None), SimpleNamespace(recipe_post=self.recipe)]

        self.assertEqual(helpers._first_item_post(items), self.recipe)

    def test_collection_entry_unsaved_uses_item_cover(self):
        fav = Favourite.objects.create(user=self.user, name="N")
        other_post = RecipePost.objects.create(
            author=self.user,
            title="X",
            description="d",
            category="dinner",
            prep_time_min=1,
            cook_time_min=1,
            image="cover.png",
        )
        FavouriteItem.objects.create(favourite=fav, recipe_post=other_post)
        entry = helpers._collection_entry(fav, self.recipe)
        self.assertFalse(entry["saved"])
        self.assertIn("cover", entry["thumb_url"])

    def test_ingredient_lists_split_shop_and_non_shop(self):
        Ingredient.objects.create(recipe_post=self.recipe, name="plain", position=1)
        Ingredient.objects.create(recipe_post=self.recipe, name="shop", shop_url=" https://x.com ", position=2)

        non_shop, shop = helpers.ingredient_lists(self.recipe)

        self.assertEqual([i.name for i in non_shop], ["plain"])
        self.assertEqual([i.name for i in shop], ["shop"])

    def test_recipe_metadata_handles_missing_times(self):
        self.recipe.prep_time_min = 0
        self.recipe.cook_time_min = 0
        self.recipe.tags = ["x"]
        self.recipe.save()
        meta = helpers.recipe_metadata(self.recipe)
        self.assertEqual(meta["cook_time"], "N/A")
        self.assertEqual(meta["author_handle"], self.user.username)

    def test_recipe_steps_returns_descriptions(self):
        RecipeStep.objects.create(recipe_post=self.recipe, position=1, description="step1")
        self.assertEqual(helpers.recipe_steps(self.recipe), ["step1"])

    def test_build_recipe_context_includes_comment_form(self):
        ctx = helpers.build_recipe_context(self.recipe, self.user, comments=["c1"])
        self.assertEqual(ctx["recipe"], self.recipe)
        self.assertIn("comment_form", ctx)
        self.assertEqual(ctx["comments"], ["c1"])

    def test_toggle_save_creates_and_removes_items(self):
        fav = Favourite.objects.create(user=self.user, name="Mine")
        saved, count = helpers.toggle_save(fav, self.recipe)
        self.assertTrue(saved)
        self.assertEqual(count, 1)
        self.assertTrue(FavouriteItem.objects.filter(favourite=fav, recipe_post=self.recipe).exists())

        saved_again, new_count = helpers.toggle_save(fav, self.recipe)
        self.assertFalse(saved_again)
        self.assertEqual(new_count, 0)

    def test_resolve_collection_with_existing_id(self):
        fav = Favourite.objects.create(user=self.user, name="Mine")
        request = self.factory.post("/", {"collection_id": fav.id})
        request.user = self.user

        found, created = helpers.resolve_collection(request, self.recipe)

        self.assertFalse(created)
        self.assertEqual(found.id, fav.id)

    def test_hx_response_or_redirect_branches(self):
        hx_req = self.factory.get("/", HTTP_HX_REQUEST="true")
        hx_req.user = self.user
        self.assertEqual(helpers.hx_response_or_redirect(hx_req, "/t").status_code, 204)
        normal = self.factory.get("/")
        normal.user = self.user
        self.assertEqual(helpers.hx_response_or_redirect(normal, "/t").status_code, 302)
