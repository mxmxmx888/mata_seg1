from unittest.mock import patch
from django.contrib import messages
from django.test import TestCase
from django.urls import reverse
from recipes.forms import UserForm
from recipes.models import User, Favourite, FavouriteItem, RecipePost, Follower, CloseFriend, FollowRequest
from recipes.views.profile_view import _profile_data_for_user, _collections_for_user
from recipes.tests.helpers import reverse_with_next

class ProfileViewTest(TestCase):

    fixtures = [
        'recipes/tests/fixtures/default_user.json',
        'recipes/tests/fixtures/other_users.json'
    ]

    def setUp(self):
        self.firebase_patch = patch("recipes.social_signals.ensure_firebase_user", return_value=None)
        self.firebase_patch.start()
        self.user = User.objects.get(username='@johndoe')
        self.url = reverse('profile')
        self.form_input = {
            'first_name': 'John2',
            'last_name': 'Doe2',
            'username': 'johndoe2',
            'email': 'johndoe2@example.org',
            'remove_avatar': False,
            'is_private': False,
        }

    def tearDown(self):
        self.firebase_patch.stop()

    def test_profile_url(self):
        self.assertEqual(self.url, '/profile/')

    def test_get_profile(self):
        self.client.login(username=self.user.username, password='Password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile/profile.html')
        form = response.context['form']
        self.assertTrue(isinstance(form, UserForm))
        self.assertEqual(form.instance, self.user)

    def test_get_profile_redirects_when_not_logged_in(self):
        redirect_url = reverse_with_next('log_in', self.url)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(redirect_url))

    def test_profile_view_nonexistent_user_raises_404(self):
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(f"{self.url}?user=@nope")
        self.assertEqual(response.status_code, 404)

    def test_unsuccesful_profile_update(self):
        self.client.login(username=self.user.username, password='Password123')
        self.form_input['username'] = '@bad'
        before_count = User.objects.count()
        response = self.client.post(self.url, self.form_input)
        after_count = User.objects.count()
        self.assertEqual(after_count, before_count)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(isinstance(form, UserForm))
        self.assertTrue(form.is_bound)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, '@johndoe')
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.email, 'johndoe@example.org')

    def test_unsuccessful_profile_update_due_to_duplicate_username(self):
        self.client.login(username=self.user.username, password='Password123')
        self.form_input['username'] = '@janedoe'
        before_count = User.objects.count()
        response = self.client.post(self.url, self.form_input)
        after_count = User.objects.count()
        self.assertEqual(after_count, before_count)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile/profile.html')
        form = response.context['form']
        self.assertTrue(isinstance(form, UserForm))
        self.assertTrue(form.is_bound)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, '@johndoe')
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.email, 'johndoe@example.org')

    def test_succesful_profile_update(self):
        self.client.login(username=self.user.username, password='Password123')
        before_count = User.objects.count()
        response = self.client.post(self.url, self.form_input, follow=True)
        after_count = User.objects.count()
        self.assertEqual(after_count, before_count)
        response_url = reverse('profile')
        self.assertRedirects(response, response_url, status_code=302, target_status_code=200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'johndoe2')
        self.assertEqual(self.user.first_name, 'John2')
        self.assertEqual(self.user.last_name, 'Doe2')
        self.assertEqual(self.user.email, 'johndoe2@example.org')

    def test_post_profile_redirects_when_not_logged_in(self):
        redirect_url = reverse_with_next('log_in', self.url)
        response = self.client.post(self.url, self.form_input)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(redirect_url))

    def test_viewing_private_other_user_shows_pending_request(self):
        other = User.objects.get(username='@janedoe')
        other.is_private = True
        other.save()
        self.client.login(username=self.user.username, password="Password123")
        FollowRequest.objects.create(requester=self.user, target=other)
        resp = self.client.get(f"{self.url}?user={other.username}")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'profile/profile.html')
        self.assertIsNotNone(resp.context["pending_follow_request"])

    def test_cancel_request_branch_redirects(self):
        other = User.objects.get(username='@janedoe')
        FollowRequest.objects.create(requester=self.user, target=other)
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(f"{self.url}?user={other.username}", {"cancel_request": "1"})
        self.assertEqual(resp.status_code, 302)

    def test_private_profile_blocks_posts_when_not_follower(self):
        other = User.objects.get(username='@janedoe')
        other.is_private = True
        other.save()
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.get(f"{self.url}?user={other.username}")
        self.assertEqual(resp.context["posts"], [])

    def test_profile_data_helper_handles_missing_fields(self):
        self.user.first_name = ""
        self.user.last_name = ""
        data = _profile_data_for_user(self.user)
        self.assertEqual(data["display_name"], self.user.username)
        self.assertEqual(data["handle"], self.user.username)

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

    def test_remove_follower_and_following(self):
        follower = User.objects.get(username='@janedoe')
        Follower.objects.create(author=self.user, follower=follower)
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(reverse("remove_follower", kwargs={"username": follower.username}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Follower.objects.filter(author=self.user, follower=follower).exists())
        Follower.objects.create(follower=self.user, author=follower)
        resp2 = self.client.post(reverse("remove_following", kwargs={"username": follower.username}))
        self.assertFalse(Follower.objects.filter(follower=self.user, author=follower).exists())

    def test_add_and_remove_close_friend(self):
        friend = User.objects.get(username='@janedoe')
        Follower.objects.create(author=self.user, follower=friend)
        self.client.login(username=self.user.username, password="Password123")
        add_resp = self.client.post(reverse("add_close_friend", kwargs={"username": friend.username}))
        self.assertTrue(CloseFriend.objects.filter(owner=self.user, friend=friend).exists())
        remove_resp = self.client.post(reverse("remove_close_friend", kwargs={"username": friend.username}))
        self.assertFalse(CloseFriend.objects.filter(owner=self.user, friend=friend).exists())

    def test_close_friend_self_redirects(self):
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(reverse("add_close_friend", kwargs={"username": self.user.username}))
        self.assertEqual(resp.status_code, 302)
        resp2 = self.client.post(reverse("remove_close_friend", kwargs={"username": self.user.username}))
        self.assertEqual(resp2.status_code, 302)

    def test_post_other_profile_redirects_to_own(self):
        other = User.objects.get(username='@janedoe')
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.post(f"{self.url}?user={other.username}", {"first_name": "X"})
        self.assertRedirects(response, reverse("profile"), status_code=302, target_status_code=200)

    def test_other_user_posts_filtered(self):
        other = User.objects.get(username='@janedoe')
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
        pal = User.objects.get(username='@janedoe')
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

    def test_profile_post_sets_success_message(self):
        self.client.login(username=self.user.username, password="Password123")
        with patch("recipes.views.profile_view.messages.add_message") as add_msg:
            try:
                resp = self.client.post(self.url, self.form_input)
            except Exception as exc:
                self.fail(str(exc))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(add_msg.called)

    def test_collections_helper_updates_last_saved(self):
        fav = Favourite.objects.create(user=self.user, name="New")
        post = RecipePost.objects.create(author=self.user, title="Newer", description="text", image="pic.png")
        item = FavouriteItem.objects.create(favourite=fav, recipe_post=post)
        FavouriteItem.objects.filter(id=item.id).update(added_at=fav.created_at.replace(year=fav.created_at.year + 1))
        cols = _collections_for_user(self.user)
        self.assertEqual(cols[0]["cover"], "pic.png")
