from unittest.mock import patch, MagicMock
from django.contrib import messages
from django.test import TestCase
from django.urls import reverse
from recipes.forms import UserForm
from recipes.models import User, Favourite, FavouriteItem, RecipePost, Follower, CloseFriend, FollowRequest
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
