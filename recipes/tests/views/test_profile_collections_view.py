from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse

from recipes.models import (
    User,
    Favourite,
    FavouriteItem,
    RecipePost,
    Follower,
    CloseFriend,
    FollowRequest,
)
from recipes.views.profile_view import _collections_for_user
from recipes.tests.test_utils import reverse_with_next


class ProfileCollectionViewTests(TestCase):
    fixtures = [
        "recipes/tests/fixtures/default_user.json",
        "recipes/tests/fixtures/other_users.json",
    ]

    def setUp(self):
        self.firebase_patch = patch("recipes.social_signals.ensure_firebase_user", return_value=None)
        self.firebase_patch.start()
        self.user = User.objects.get(username="@johndoe")
        self.url = reverse("profile")
        self.form_input = {
            "first_name": "John2",
            "last_name": "Doe2",
            "username": "johndoe2",
            "email": "johndoe2@example.org",
            "remove_avatar": False,
            "is_private": False,
        }

    def tearDown(self):
        self.firebase_patch.stop()

    def test_collections_helper_builds_payload(self):
        fav = Favourite.objects.create(user=self.user, name="List")
        post = RecipePost.objects.create(author=self.user, title="Pie", description="d", image="img.png")
        FavouriteItem.objects.create(favourite=fav, recipe_post=post)
        cols = _collections_for_user(self.user)
        self.assertEqual(cols[0]["title"], "List")
        self.assertEqual(cols[0]["count"], 1)

    def test_collections_helper_uses_first_post_with_image(self):
        fav = Favourite.objects.create(user=self.user, name="List")
        no_image_post = RecipePost.objects.create(author=self.user, title="No image", description="d")
        with_image_post = RecipePost.objects.create(author=self.user, title="With image", description="d", image="cover.png")
        FavouriteItem.objects.create(favourite=fav, recipe_post=no_image_post)
        FavouriteItem.objects.create(favourite=fav, recipe_post=with_image_post)

        cols = _collections_for_user(self.user)
        self.assertEqual(cols[0]["cover"], "cover.png")
        self.assertTrue(cols[0]["has_image"])

    def test_collections_helper_marks_outline_when_no_images(self):
        fav = Favourite.objects.create(user=self.user, name="Empty images")
        first = RecipePost.objects.create(author=self.user, title="One", description="d")
        second = RecipePost.objects.create(author=self.user, title="Two", description="d")
        FavouriteItem.objects.create(favourite=fav, recipe_post=first)
        FavouriteItem.objects.create(favourite=fav, recipe_post=second)

        cols = _collections_for_user(self.user)
        self.assertIsNone(cols[0]["cover"])
        self.assertFalse(cols[0]["has_image"])

    def test_collections_helper_handles_empty_collection(self):
        Favourite.objects.create(user=self.user, name="Empty")
        cols = _collections_for_user(self.user)
        self.assertEqual(cols[0]["count"], 0)

    def test_collections_overview_renders(self):
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.get(reverse("collections"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "app/collections.html")

    def test_collections_overview_ajax_paginates(self):
        self.client.login(username=self.user.username, password="Password123")
        for i in range(40):
            Favourite.objects.create(user=self.user, name=f"Fav {i}")

        resp = self.client.get(reverse("collections"), {"page": "2"}, HTTP_HX_REQUEST="true")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("partials/collections/collection_cards.html", [t.name for t in resp.templates])
        total = Favourite.objects.filter(user=self.user).count()
        expected_len = min(35, max(0, total - 35))
        self.assertEqual(len(resp.context["collections"]), expected_len)

    def test_collections_overview_sets_pagination_flags(self):
        self.client.login(username=self.user.username, password="Password123")
        for i in range(36):
            Favourite.objects.create(user=self.user, name=f"Fav {i}")

        resp = self.client.get(reverse("collections"))

        self.assertTrue(resp.context["collections_has_more"])
        self.assertEqual(resp.context["collections_next_page"], 2)

    def test_collection_detail_lists_posts(self):
        fav = Favourite.objects.create(user=self.user, name="My stuff")
        post = RecipePost.objects.create(author=self.user, title="Soup", description="d")
        FavouriteItem.objects.create(favourite=fav, recipe_post=post)
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("collection_detail", kwargs={"slug": fav.id})
        resp = self.client.get(url)
        self.assertContains(resp, "Soup")

    def test_collection_detail_404_when_missing(self):
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("collection_detail", kwargs={"slug": "00000000-0000-0000-0000-000000000000"})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_delete_collection_returns_json_when_hx(self):
        fav = Favourite.objects.create(user=self.user, name="Old")
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("delete_collection", kwargs={"slug": fav.id})
        resp = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(resp.json()["deleted"], True)

    def test_delete_collection_redirects_when_not_ajax(self):
        fav = Favourite.objects.create(user=self.user, name="Old")
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("delete_collection", kwargs={"slug": fav.id})
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("collections"), target_status_code=200)

    def test_update_collection_updates_title(self):
        fav = Favourite.objects.create(user=self.user, name="Old")
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("update_collection", kwargs={"slug": fav.id})
        resp = self.client.post(url, {"title": "New"}, HTTP_HX_REQUEST="true")
        fav.refresh_from_db()
        self.assertEqual(fav.name, "New")
        self.assertEqual(resp.json()["title"], "New")

    def test_update_collection_redirects_when_not_ajax(self):
        fav = Favourite.objects.create(user=self.user, name="Old")
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("update_collection", kwargs={"slug": fav.id})
        resp = self.client.post(url, {"title": "Again"})
        fav.refresh_from_db()
        self.assertRedirects(resp, reverse("collection_detail", kwargs={"slug": fav.id}), target_status_code=200)

    def test_update_collection_blank_non_ajax_redirects_without_change(self):
        fav = Favourite.objects.create(user=self.user, name="Keep")
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("update_collection", kwargs={"slug": fav.id})
        resp = self.client.post(url, {"title": "   "})
        fav.refresh_from_db()
        self.assertEqual(fav.name, "Keep")
        self.assertRedirects(resp, reverse("collection_detail", kwargs={"slug": fav.id}), target_status_code=200)

    def test_update_collection_invalid_name_returns_400_ajax(self):
        fav = Favourite.objects.create(user=self.user, name="Old")
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("update_collection", kwargs={"slug": fav.id})
        too_long = "x" * 300
        resp = self.client.post(url, {"title": too_long}, HTTP_HX_REQUEST="true")
        fav.refresh_from_db()
        self.assertEqual(fav.name, "Old")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("errors", resp.json())

    def test_update_collection_invalid_name_redirects_when_not_ajax(self):
        fav = Favourite.objects.create(user=self.user, name="Old")
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("update_collection", kwargs={"slug": fav.id})
        too_long = "x" * 300
        resp = self.client.post(url, {"title": too_long})
        fav.refresh_from_db()
        self.assertEqual(fav.name, "Old")
        self.assertRedirects(resp, reverse("collection_detail", kwargs={"slug": fav.id}), target_status_code=200)

    def test_remove_follower_and_following(self):
        follower = User.objects.get(username="@janedoe")
        Follower.objects.create(author=self.user, follower=follower)
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(reverse("remove_follower", kwargs={"username": follower.username}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Follower.objects.filter(author=self.user, follower=follower).exists())
        Follower.objects.create(follower=self.user, author=follower)
        resp2 = self.client.post(reverse("remove_following", kwargs={"username": follower.username}))
        self.assertFalse(Follower.objects.filter(follower=self.user, author=follower).exists())

    def test_add_and_remove_close_friend(self):
        friend = User.objects.get(username="@janedoe")
        Follower.objects.create(author=self.user, follower=friend)
        self.client.login(username=self.user.username, password="Password123")
        add_resp = self.client.post(reverse("add_close_friend", kwargs={"username": friend.username}))
        self.assertTrue(CloseFriend.objects.filter(owner=self.user, friend=friend).exists())
        remove_resp = self.client.post(reverse("remove_close_friend", kwargs={"username": friend.username}))
        self.assertFalse(CloseFriend.objects.filter(owner=self.user, friend=friend).exists())

    def test_add_close_friend_self_ajax_returns_error(self):
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(reverse("add_close_friend", kwargs={"username": self.user.username}), HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 400)

    def test_close_friend_self_redirects(self):
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(reverse("add_close_friend", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 302)
        resp2 = self.client.post(reverse("remove_close_friend", kwargs={"username": self.user.username}))
        self.assertEqual(resp2.status_code, 302)

    def test_post_other_profile_redirects_to_own(self):
        other = User.objects.get(username="@janedoe")
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.post(f"{self.url}?user={other.username}", {"first_name": "X"})
        self.assertRedirects(response, reverse("profile"), status_code=302, target_status_code=200)

    def test_other_user_posts_filtered(self):
        other = User.objects.get(username="@janedoe")
        RecipePost.objects.create(author=other, title="Note", description="d")
        self.client.login(username=self.user.username, password="Password123")
        with patch("recipes.views.profile_view.privacy_service.filter_visible_posts") as filt:
            filt.side_effect = lambda qs, viewer: qs
            resp = self.client.get(f"{self.url}?user={other.username}")
        self.assertTrue(resp.context["posts"])
        filt.assert_called()

    def test_update_collection_keeps_title_when_blank(self):
        fav = Favourite.objects.create(user=self.user, name="Stay")
        self.client.login(username=self.user.username, password="Password123")
        url = reverse("update_collection", kwargs={"slug": fav.id})
        resp = self.client.post(url, {"title": "   "}, HTTP_HX_REQUEST="true")
        fav.refresh_from_db()
        self.assertEqual(fav.name, "Stay")
        self.assertEqual(resp.json()["title"], "Stay")

    def test_remove_self_follower_paths_redirect(self):
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(reverse("remove_follower", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 302)
        resp2 = self.client.post(reverse("remove_following", kwargs={"username": self.user.username}))
        self.assertEqual(resp2.status_code, 302)

    def test_add_close_friend_without_follow_redirects(self):
        pal = User.objects.get(username="@janedoe")
        self.client.login(username=self.user.username, password="Password123")
        result = self.client.post(reverse("add_close_friend", kwargs={"username": pal.username}))
        self.assertFalse(CloseFriend.objects.filter(owner=self.user, friend=pal).exists())
        self.assertEqual(result.status_code, 302)

    def test_collection_detail_skips_items_without_post(self):
        fav = Favourite.objects.create(user=self.user, name="Empty")
        self.client.login(username=self.user.username, password="Password123")

        class FakeQS(list):
            def select_related(self, *args, **kwargs):
                return self

        fake_qs = FakeQS([type("Item", (), {"recipe_post": None})()])
        with patch("recipes.views.profile_view.FavouriteItem.objects") as mgr:
            mgr.filter.return_value = fake_qs
            resp = self.client.get(reverse("collection_detail", kwargs={"slug": fav.id}))
        self.assertEqual(list(resp.context["posts"]), [])

    def test_collection_detail_handles_qs_without_order_by(self):
        fav = Favourite.objects.create(user=self.user, name="No order")
        self.client.login(username=self.user.username, password="Password123")

        class FakeQS(list):
            def select_related(self, *args, **kwargs):
                return self

        fake_items = FakeQS([type("Item", (), {"recipe_post": None})()])
        with patch("recipes.views.collection_views.FavouriteItem.objects") as mgr:
            mgr.filter.return_value = fake_items
            resp = self.client.get(reverse("collection_detail", kwargs={"slug": fav.id}))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["posts"], [])

    def test_profile_post_sets_success_message(self):
        self.client.login(username=self.user.username, password="Password123")
        with patch("recipes.views.profile_view.messages.add_message") as add_msg:
            resp = self.client.post(self.url, self.form_input)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(add_msg.called)

    def test_collections_helper_updates_last_saved(self):
        fav = Favourite.objects.create(user=self.user, name="New")
        post = RecipePost.objects.create(author=self.user, title="Newer", description="text", image="pic.png")
        item = FavouriteItem.objects.create(favourite=fav, recipe_post=post)
        FavouriteItem.objects.filter(id=item.id).update(added_at=fav.created_at.replace(year=fav.created_at.year + 1))
        cols = _collections_for_user(self.user)
        self.assertEqual(cols[0]["cover"], "pic.png")

    def test_ajax_error_paths_for_follow_management(self):
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(reverse("remove_follower", kwargs={"username": self.user.username}), HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 400)
        resp2 = self.client.post(reverse("remove_following", kwargs={"username": self.user.username}), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp2.status_code, 400)
        pal = User.objects.get(username="@janedoe")
        resp3 = self.client.post(reverse("add_close_friend", kwargs={"username": pal.username}), HTTP_HX_REQUEST="true")
        self.assertEqual(resp3.status_code, 400)
        resp4 = self.client.post(reverse("remove_close_friend", kwargs={"username": self.user.username}), HTTP_HX_REQUEST="true")
        self.assertEqual(resp4.status_code, 400)

    def test_ajax_success_paths_for_follow_management(self):
        pal = User.objects.get(username="@janedoe")
        follower = User.objects.create_user(username="@other", email="o@example.com", password="Password123")
        Follower.objects.create(author=self.user, follower=follower)
        Follower.objects.create(follower=self.user, author=pal)
        Follower.objects.create(author=self.user, follower=pal)
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(reverse("remove_follower", kwargs={"username": follower.username}), HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("removed", resp.json()["status"])
        resp2 = self.client.post(reverse("remove_following", kwargs={"username": pal.username}), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp2.status_code, 200)
        resp3 = self.client.post(reverse("add_close_friend", kwargs={"username": pal.username}), HTTP_HX_REQUEST="true")
        self.assertEqual(resp3.status_code, 200)
        resp4 = self.client.post(reverse("remove_close_friend", kwargs={"username": pal.username}), HTTP_HX_REQUEST="true")
        self.assertEqual(resp4.status_code, 200)

    def test_collections_helper_skips_items_without_recipe(self):
        class FakeFav:
            def __init__(self, user):
                self.id = "abc"
                self.name = "Ghost"
                self.user = user
                self.cover_post = None
                from django.utils import timezone

                self.created_at = timezone.now()
                self.items = self

            def select_related(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return [type("Item", (), {"recipe_post": None, "added_at": None})()]

        with patch("recipes.views.profile_view.Favourite.objects") as fav_mgr:
            class FakeFavQS(list):
                def prefetch_related(self, *args, **kwargs):
                    return self

            fav_mgr.filter.return_value = FakeFavQS([FakeFav(self.user)])
            cols = _collections_for_user(self.user)
        self.assertEqual(cols[0]["count"], 0)

    def test_collections_helper_respects_cover_post_and_existing_images(self):
        cover = RecipePost.objects.create(author=self.user, title="Cover", description="d", image="cover.png")

        class Item:
            def __init__(self, recipe_post, added_at):
                self.recipe_post = recipe_post
                self.added_at = added_at

        class FakeQS(list):
            def select_related(self, *args, **kwargs):
                return self

            def order_by(self, *args, **kwargs):
                return self

        class FakeFav:
            def __init__(self, cover_post, created_at, items):
                self.id = "fav"
                self.name = "Has cover"
                self.cover_post = cover_post
                self.created_at = created_at
                self.items = items

        first = RecipePost.objects.create(author=self.user, title="First", description="d", image="first.png")
        second = RecipePost.objects.create(author=self.user, title="Second", description="d", image="second.png")
        fake_items = FakeQS([Item(first, None), Item(second, cover.created_at)])
        fake_fav = FakeFav(cover, cover.created_at, fake_items)
        with patch("recipes.views.profile_view.Favourite.objects") as fav_mgr:
            class FakeFavQS(list):
                def prefetch_related(self, *args, **kwargs):
                    return self

            fav_mgr.filter.return_value = FakeFavQS([fake_fav])
            cols = _collections_for_user(self.user)

        self.assertEqual(cols[0]["cover"], "cover.png")
