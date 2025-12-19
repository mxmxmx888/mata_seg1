from unittest.mock import MagicMock, patch

from django.http import Http404
from django.urls import reverse

from recipes.models.comment import Comment
from recipes.models.favourite import Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.models.like import Like
from recipes.models.recipe_post import RecipePost
from recipes.tests.views.base import RecipeViewTestCase, add_session_and_messages
from recipes.views import recipe_views
from recipes.views.recipe_views import (
    add_comment,
    delete_comment,
    recipe_detail,
    toggle_favourite,
    toggle_follow,
    toggle_like,
)


class RecipeViewActionsTests(RecipeViewTestCase):
    def test_recipe_detail_authenticated_context(self):
        fav = Favourite.objects.create(user=self.user, name="favourites")
        FavouriteItem.objects.create(favourite=fav, recipe_post=self.post)
        Like.objects.create(user=self.user, recipe_post=self.post)

        self.client.login(username=self.user.username, password="Password123")
        url = reverse("recipe_detail", args=[self.post.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user_liked"])
        self.assertTrue(response.context["user_saved"])
        self.assertTrue(response.context["save_collections"][0]["saved"])

    @patch("recipes.views.recipe_views.privacy_service.can_view_post", return_value=False)
    def test_recipe_detail_respects_privacy(self, _mock_can_view):
        request = self.factory.get(f"/fake/recipe/{self.post.id}/")
        request.user = self.user
        add_session_and_messages(request)

        with self.assertRaises(Http404):
            recipe_detail(request, post_id=self.post.id)

    def test_toggle_like_creates_then_deletes_like(self):
        req1 = self.factory.post(f"/fake/recipe/{self.post.id}/like/")
        req1.user = self.user
        add_session_and_messages(req1)
        res1 = toggle_like(req1, post_id=self.post.id)
        self.assertEqual(res1.status_code, 302)
        self.assertTrue(Like.objects.filter(user=self.user, recipe_post=self.post).exists())

        req2 = self.factory.post(f"/fake/recipe/{self.post.id}/like/")
        req2.user = self.user
        add_session_and_messages(req2)
        res2 = toggle_like(req2, post_id=self.post.id)
        self.assertEqual(res2.status_code, 302)
        self.assertFalse(Like.objects.filter(user=self.user, recipe_post=self.post).exists())

    def test_toggle_like_hx_returns_204(self):
        req = self.factory.post(f"/fake/recipe/{self.post.id}/like/", HTTP_HX_REQUEST="true")
        req.user = self.user
        add_session_and_messages(req)

        response = toggle_like(req, post_id=self.post.id)
        self.assertEqual(response.status_code, 204)

    def test_toggle_favourite_creates_collection_and_item_and_updates_saved_count(self):
        self.assertEqual(self.post.saved_count, 0)

        request = self.factory.post(f"/fake/recipe/{self.post.id}/save/", data={})
        request.user = self.user
        add_session_and_messages(request)

        response = toggle_favourite(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)

        fav = Favourite.objects.get(user=self.user, name="favourites")
        self.assertTrue(FavouriteItem.objects.filter(favourite=fav, recipe_post=self.post).exists())

        self.post.refresh_from_db()
        self.assertEqual(self.post.saved_count, 1)

    def test_add_comment_creates_comment(self):
        request = self.factory.post(
            f"/fake/recipe/{self.post.id}/comment/", data={"text": "Nice!"}
        )
        request.user = self.user
        add_session_and_messages(request)

        response = add_comment(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(recipe_post=self.post, user=self.user).exists())

    def test_add_comment_invalid_shows_error_and_redirects(self):
        request = self.factory.post(f"/fake/recipe/{self.post.id}/comment/", data={})
        request.user = self.user
        add_session_and_messages(request)

        response = add_comment(request, post_id=self.post.id)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(recipe_post=self.post, user=self.user).exists())

    def test_delete_comment_blocked_for_non_owner(self):
        comment = Comment.objects.create(recipe_post=self.post, user=self.user, text="Mine")

        request = self.factory.post(f"/fake/comment/{comment.id}/delete/")
        request.user = self.other
        add_session_and_messages(request)

        response = delete_comment(request, comment_id=comment.id)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(id=comment.id).exists())

    def test_delete_comment_deletes_for_owner(self):
        comment = Comment.objects.create(recipe_post=self.post, user=self.user, text="Mine")

        request = self.factory.post(f"/fake/comment/{comment.id}/delete/")
        request.user = self.user
        add_session_and_messages(request)

        response = delete_comment(request, comment_id=comment.id)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())

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

    def test_delete_my_recipe_requires_post(self):
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("delete_my_recipe", args=[self.post.id])
        response = self.client.get(url)
        self.assertRedirects(response, reverse("recipe_detail", args=[self.post.id]))

    def test_delete_my_recipe_post_deletes(self):
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("delete_my_recipe", args=[self.post.id])
        response = self.client.post(url)
        self.assertRedirects(response, reverse("profile"))
        self.assertFalse(RecipePost.objects.filter(id=self.post.id).exists())

    def test_toggle_favourite_ajax_creates_and_returns_json(self):
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("toggle_favourite", args=[self.post.id])

        response = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["saved"])
        self.assertEqual(payload["saved_count"], 1)
        self.assertTrue(payload["collection"]["created"])

        response2 = self.client.post(url, HTTP_HX_REQUEST="true")
        payload2 = response2.json()
        self.assertFalse(payload2["saved"])
        self.assertEqual(payload2["saved_count"], 0)

    def test_toggle_favourite_existing_collection_unsaves(self):
        self.client.login(username=self.user.username, password="Password123")
        fav = Favourite.objects.create(user=self.user, name="custom")
        FavouriteItem.objects.create(favourite=fav, recipe_post=self.post)
        RecipePost.objects.filter(id=self.post.id).update(saved_count=1)

        url = reverse("toggle_favourite", args=[self.post.id])
        response = self.client.post(
            url, {"collection_id": str(fav.id)}, HTTP_HX_REQUEST="true"
        )
        payload = response.json()
        self.assertFalse(payload["saved"])
        self.assertEqual(payload["saved_count"], 0)

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

    @patch.object(recipe_views, "follow_service_factory")
    def test_toggle_follow_hx_returns_204(self, mock_factory):
        self.client.login(username=self.user.username, password="Password123")
        mock_service = MagicMock()
        mock_factory.return_value = mock_service

        url = reverse("toggle_follow", args=[self.other.username])
        response = self.client.post(url, HTTP_HX_REQUEST="true")

        mock_service.toggle_follow.assert_called_once_with(self.other)
        self.assertEqual(response.status_code, 204)

    def test_toggle_follow_self_non_hx_redirects(self):
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("toggle_follow", args=[self.user.username])
        response = self.client.post(url)
        self.assertRedirects(response, reverse("dashboard"))
