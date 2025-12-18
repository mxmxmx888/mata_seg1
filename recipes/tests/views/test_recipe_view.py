from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import Http404
from django.test import TestCase, RequestFactory
from django.urls import reverse

from recipes.models.recipe_post import RecipePost
from recipes.models.like import Like
from recipes.models.comment import Comment
from recipes.models.favourite import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.views import recipe_views

# Import the actual view functions
from recipes.views.recipe_views import (
    recipe_create,
    recipe_edit,
    recipe_detail,
    toggle_like,
    toggle_favourite,
    add_comment,
    delete_comment,
)

User = get_user_model()


def _add_session_and_messages(request):
    """Attach session + messages to a RequestFactory request (so login_required and messages work)."""
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()

    # Messages framework expects request._messages
    request._messages = FallbackStorage(request)
    return request


class RecipeViewsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="user_a",
            email="user_a@example.org",
            password="Password123",
        )
        self.other = User.objects.create_user(
            username="user_b",
            email="user_b@example.org",
            password="Password123",
        )

        self.post = RecipePost.objects.create(
            author=self.user,
            title="Test Post",
            description="Desc",
            prep_time_min=5,
            cook_time_min=10,
            tags=["quick"],
            category="Dinner",
            visibility=RecipePost.VISIBILITY_PUBLIC,
        )

    # ---------------------------
    # Login-required behaviour
    # ---------------------------
    def test_recipe_create_requires_login(self):
        request = self.factory.get("/fake/recipe/create/")
        request.user = AnonymousUser()
        _add_session_and_messages(request)

        response = recipe_create(request)
        self.assertEqual(response.status_code, 302)  # redirected to login

    def test_recipe_detail_requires_login(self):
        request = self.factory.get(f"/fake/recipe/{self.post.id}/")
        request.user = AnonymousUser()
        _add_session_and_messages(request)

        response = recipe_detail(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)

    # ---------------------------
    # recipe_create
    # ---------------------------
    @patch("recipes.views.recipe_views.RecipePostForm")
    def test_recipe_create_post_valid_creates_recipe_and_redirects(self, MockForm):
        # Fake form instance
        form = MagicMock()
        form.is_valid.return_value = True
        form.cleaned_data = {
            "title": "Created title",
            "description": "Created desc",
            "prep_time_min": 3,
            "cook_time_min": 7,
            "nutrition": "kcal=500",
            "category": "Lunch",
            "visibility": RecipePost.VISIBILITY_PUBLIC,
        }
        form.parse_tags.return_value = ["tag1", "tag2"]
        form.create_ingredients.return_value = None
        form.create_steps.return_value = None
        form.create_images.return_value = None

        MockForm.return_value = form

        request = self.factory.post("/fake/recipe/create/", data={"title": "x"})
        request.user = self.user
        _add_session_and_messages(request)

        # Ensure privacy isn't blocking anything
        with patch("recipes.views.recipe_views.PrivacyService.can_view_post", return_value=True):
            response = recipe_create(request)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(RecipePost.objects.filter(title="Created title", author=self.user).exists())

    # ---------------------------
    # recipe_edit
    # ---------------------------
    def test_recipe_edit_non_author_gets_404(self):
        request = self.factory.get(f"/fake/recipe/{self.post.id}/edit/")
        request.user = self.other
        _add_session_and_messages(request)

        with self.assertRaises(Http404):
            recipe_edit(request, post_id=self.post.id)

    @patch("recipes.views.recipe_views.RecipePostForm")
    def test_recipe_edit_post_valid_updates_recipe(self, MockForm):
        form = MagicMock()
        form.is_valid.return_value = True
        form.cleaned_data = {
            "title": "Updated",
            "description": "Updated desc",
            "prep_time_min": 11,
            "cook_time_min": 22,
            "nutrition": "kcal=700",
            "category": "Breakfast",
            "visibility": RecipePost.VISIBILITY_PUBLIC,
        }
        form.parse_tags.return_value = ["newtag"]
        form.create_ingredients.return_value = None
        form.create_steps.return_value = None
        form.create_images.return_value = None
        MockForm.return_value = form

        request = self.factory.post(f"/fake/recipe/{self.post.id}/edit/", data={"title": "Updated"})
        request.user = self.user
        _add_session_and_messages(request)

        response = recipe_edit(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)

        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Updated")
        self.assertEqual(self.post.prep_time_min, 11)
        self.assertEqual(self.post.cook_time_min, 22)

    # ---------------------------
    # toggle_like
    # ---------------------------
    def test_toggle_like_creates_then_deletes_like(self):
        # Like created
        req1 = self.factory.post(f"/fake/recipe/{self.post.id}/like/")
        req1.user = self.user
        _add_session_and_messages(req1)
        res1 = toggle_like(req1, post_id=self.post.id)
        self.assertEqual(res1.status_code, 302)
        self.assertTrue(Like.objects.filter(user=self.user, recipe_post=self.post).exists())

        # Like deleted
        req2 = self.factory.post(f"/fake/recipe/{self.post.id}/like/")
        req2.user = self.user
        _add_session_and_messages(req2)
        res2 = toggle_like(req2, post_id=self.post.id)
        self.assertEqual(res2.status_code, 302)
        self.assertFalse(Like.objects.filter(user=self.user, recipe_post=self.post).exists())

    # ---------------------------
    # toggle_favourite
    # ---------------------------
    def test_toggle_favourite_creates_collection_and_item_and_updates_saved_count(self):
        self.assertEqual(self.post.saved_count, 0)

        request = self.factory.post(f"/fake/recipe/{self.post.id}/save/", data={})
        request.user = self.user
        _add_session_and_messages(request)

        response = toggle_favourite(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)

        fav = Favourite.objects.get(user=self.user, name="favourites")
        self.assertTrue(FavouriteItem.objects.filter(favourite=fav, recipe_post=self.post).exists())

        self.post.refresh_from_db()
        self.assertEqual(self.post.saved_count, 1)

    # ---------------------------
    # add_comment + delete_comment
    # ---------------------------
    def test_add_comment_creates_comment(self):
        request = self.factory.post(f"/fake/recipe/{self.post.id}/comment/", data={"text": "Nice!"})
        request.user = self.user
        _add_session_and_messages(request)

        response = add_comment(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(recipe_post=self.post, user=self.user).exists())

    def test_delete_comment_blocked_for_non_owner(self):
        comment = Comment.objects.create(recipe_post=self.post, user=self.user, text="Mine")

        request = self.factory.post(f"/fake/comment/{comment.id}/delete/")
        request.user = self.other
        _add_session_and_messages(request)

        response = delete_comment(request, comment_id=comment.id)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(id=comment.id).exists())  # still there

    def test_delete_comment_deletes_for_owner(self):
        comment = Comment.objects.create(recipe_post=self.post, user=self.user, text="Mine")

        request = self.factory.post(f"/fake/comment/{comment.id}/delete/")
        request.user = self.user
        _add_session_and_messages(request)

        response = delete_comment(request, comment_id=comment.id)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())

    # ---------------------------
    # saved_recipes
    # ---------------------------
    def test_saved_recipes_deduplicates(self):
        fav1 = Favourite.objects.create(user=self.user, name="favourites")
        fav2 = Favourite.objects.create(user=self.user, name="quick dinners")
        FavouriteItem.objects.create(favourite=fav1, recipe_post=self.post)
        FavouriteItem.objects.create(favourite=fav2, recipe_post=self.post)

        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(reverse("saved_recipes"))

        self.assertEqual(response.status_code, 200)
        posts = response.context["posts"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].id, self.post.id)

    # ---------------------------
    # toggle_favourite HX branch
    # ---------------------------
    def test_toggle_favourite_ajax_creates_and_returns_json(self):
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("toggle_favourite", args=[self.post.id])

        response = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["saved"])
        self.assertEqual(payload["saved_count"], 1)
        self.assertTrue(payload["collection"]["created"])

        # second toggle should unsave and decrement count
        response2 = self.client.post(url, HTTP_HX_REQUEST="true")
        payload2 = response2.json()
        self.assertFalse(payload2["saved"])
        self.assertEqual(payload2["saved_count"], 0)

    # ---------------------------
    # toggle_follow
    # ---------------------------
    def test_toggle_follow_self_returns_204_for_hx(self):
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("toggle_follow", args=[self.user.username])
        response = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 204)

    @patch.object(recipe_views, "follow_service_factory")
    def test_toggle_follow_calls_service_for_normal_request(self, mock_factory):
        self.client.login(username=self.user.username, password="Password123")
        target = self.other
        mock_service = MagicMock()
        mock_factory.return_value = mock_service

        url = reverse("toggle_follow", args=[target.username])
        response = self.client.post(url)

        mock_factory.assert_called_once_with(self.user)
        mock_service.toggle_follow.assert_called_once_with(target)
        self.assertEqual(response.status_code, 302)
