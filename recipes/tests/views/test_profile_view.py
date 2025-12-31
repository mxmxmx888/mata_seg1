from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from django.contrib import messages
from django.test import TestCase
from django.urls import reverse
from recipes.forms import UserForm
from recipes.models import User, Favourite, FavouriteItem, RecipePost, Follower, CloseFriend, FollowRequest
from recipes.views import profile_view
from recipes.views import profile_view_logic as logic
from recipes.views.profile_view import _profile_data_for_user, _collections_for_user
from recipes.tests.test_utils import reverse_with_next

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

    def test_profile_post_valid_without_changes_skips_save(self):
        self.client.login(username=self.user.username, password="Password123")
        with patch("recipes.views.profile_view.UserForm") as form_cls:
            form = MagicMock()
            form.is_valid.return_value = True
            form.changed_data = []
            form.save.return_value = None
            form_cls.return_value = form
            resp = self.client.post(self.url, {"first_name": "John"})
        self.assertEqual(resp.status_code, 302)
        form.save.assert_not_called()

    def test_profile_post_with_avatar_change_skips_message(self):
        self.client.login(username=self.user.username, password="Password123")
        with patch("recipes.views.profile_view.UserForm") as form_cls, patch("recipes.views.profile_view.messages.add_message") as add_msg:
            form = MagicMock()
            form.is_valid.return_value = True
            form.changed_data = ["avatar"]
            form.save.return_value = None
            form_cls.return_value = form
            resp = self.client.post(self.url, {"first_name": "John"})
        self.assertEqual(resp.status_code, 302)
        add_msg.assert_not_called()

    def test_profile_post_with_non_avatar_changes_adds_message(self):
        self.client.login(username=self.user.username, password="Password123")
        with patch("recipes.views.profile_view.UserForm") as form_cls, patch("recipes.views.profile_view.messages.add_message") as add_msg:
            form = MagicMock()
            form.is_valid.return_value = True
            form.changed_data = ["first_name"]
            form.save.return_value = None
            form_cls.return_value = form
            resp = self.client.post(self.url, {"first_name": "John"})
        self.assertEqual(resp.status_code, 302)
        add_msg.assert_called_once()

    def test_profile_posts_only_hx_returns_partial(self):
        self.client.login(username=self.user.username, password="Password123")
        RecipePost.objects.create(author=self.user, title="P1", description="d")
        response = self.client.get(f"{self.url}?posts_only=1", HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertIn("partials/feed/feed_cards.html", [t.name for t in response.templates])
        self.assertIn(b"P1", response.content)

    def test_profile_pagination_sets_flags(self):
        self.client.login(username=self.user.username, password="Password123")
        for i in range(13):
            RecipePost.objects.create(author=self.user, title=f"Post {i}", description="d")

        response = self.client.get(self.url)

        self.assertEqual(len(response.context["posts"]), 12)
        self.assertTrue(response.context["posts_has_more"])
        self.assertEqual(response.context["posts_next_page"], 2)

    def test_apply_follow_visibility_hides_when_private_and_not_following(self):
        private_user = User.objects.get(username='@janedoe')
        private_user.is_private = True
        private_user.save()
        followers = {"users": [self.user], "has_more": True, "next_page": 2, "visible": True}
        following = {"users": [self.user], "has_more": False, "next_page": None, "visible": True}

        hidden_followers, hidden_following = logic.apply_follow_visibility(private_user, self.user, False, followers, following)

        self.assertFalse(hidden_followers["visible"])
        self.assertEqual(hidden_followers["users"], [])
        self.assertFalse(hidden_following["visible"])
        self.assertEqual(hidden_following["users"], [])

    def test_follow_list_selection_close_friends_requires_owner(self):
        private_user = User.objects.get(username='@janedoe')
        response = logic.follow_list_selection("close_friends", private_user, False, SimpleNamespace(follower_model=Follower))
        self.assertEqual(response.status_code, 403)

    def test_profile_posts_respects_privacy_block(self):
        class StubPrivacy:
            def __init__(self, allow): self.allow = allow
            def can_view_profile(self, viewer, profile_user): return self.allow
            def filter_visible_posts(self, qs, viewer): return qs

        deps = SimpleNamespace(
            privacy_service=StubPrivacy(False),
            recipe_post_model=RecipePost,
            post_repo=SimpleNamespace(list_for_user=lambda *args, **kwargs: RecipePost.objects.all()),
        )
        profile_user = User.objects.get(username='@janedoe')

        posts_qs, can_view = logic.profile_posts(profile_user, self.user, deps)

        self.assertFalse(can_view)
        self.assertEqual(posts_qs.count(), 0)

    def test_pending_follow_request_returns_request(self):
        private_user = User.objects.get(username='@janedoe')
        private_user.is_private = True
        private_user.save()
        fr = FollowRequest.objects.create(requester=self.user, target=private_user, status=FollowRequest.STATUS_PENDING)
        deps = SimpleNamespace(follow_request_model=FollowRequest)

        result = logic.pending_follow_request(self.user, private_user, False, deps)

        self.assertEqual(result, fr)

    def test_profile_posts_hidden_when_privacy_denies(self):
        self.client.login(username=self.user.username, password="Password123")
        with patch.object(profile_view.privacy_service, "can_view_profile", return_value=False):
            response = self.client.get(self.url)

        self.assertEqual(response.context["posts"], [])
        self.assertFalse(response.context["can_view_profile"])

    def test_profile_get_for_other_user_has_no_form(self):
        other = User.objects.get(username='@janedoe')
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(f"{self.url}?user={other.username}")
        self.assertIsNone(response.context["form"])

    def test_profile_cancel_request_post_calls_service_and_redirects(self):
        other = User.objects.get(username='@janedoe')
        self.client.login(username=self.user.username, password="Password123")
        with patch.object(profile_view, "follow_service_factory") as factory:
            service = MagicMock()
            factory.return_value = service
            resp = self.client.post(f"{self.url}?user={other.username}", {"cancel_request": "1"})
        self.assertEqual(resp.status_code, 302)
        service.cancel_request.assert_called_once_with(other)

    def test_profile_posts_for_other_user_are_filtered_by_privacy(self):
        other = User.objects.get(username='@janedoe')
        RecipePost.objects.create(author=other, title="Hidden", description="d")
        self.client.login(username=self.user.username, password="Password123")
        with patch.object(profile_view.privacy_service, "filter_visible_posts", wraps=profile_view.privacy_service.filter_visible_posts) as filter_posts:
            resp = self.client.get(f"{self.url}?user={other.username}")
        self.assertEqual(resp.status_code, 200)
        filter_posts.assert_called()

    def test_profile_post_for_other_user_redirects_to_profile(self):
        other = User.objects.get(username='@janedoe')
        self.client.login(username=self.user.username, password="Password123")
        resp = self.client.post(f"{self.url}?user={other.username}", {"first_name": "X"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith(reverse("profile")))
