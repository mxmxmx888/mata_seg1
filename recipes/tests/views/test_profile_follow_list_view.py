from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from recipes.models import Follower, User
import recipes.views.profile_view as profile_view


class ProfileFollowListViewTest(TestCase):
    fixtures = [
        'recipes/tests/fixtures/default_user.json',
        'recipes/tests/fixtures/other_users.json'
    ]

    def setUp(self):
        self.firebase_patch = patch("recipes.social_signals.ensure_firebase_user", return_value=None)
        self.firebase_patch.start()
        self.user = User.objects.get(username='@johndoe')

    def tearDown(self):
        self.firebase_patch.stop()

    def test_follow_context_hides_lists_for_private_when_not_following(self):
        private_user = User.objects.get(username='@janedoe')
        private_user.is_private = True
        private_user.save()
        extra_follower = User.objects.create_user(username="@viewerx", email="v@example.org", password="Password123")
        Follower.objects.create(author=private_user, follower=extra_follower)

        ctx = profile_view._follow_context(private_user, self.user)

        self.assertEqual(ctx["followers_count"], 1)
        self.assertFalse(ctx["can_view_follow_lists"])
        self.assertEqual(ctx["followers_users"], [])
        self.assertEqual(ctx["following_users"], [])

    def test_follow_context_paginates_follow_lists(self):
        self.client.login(username=self.user.username, password="Password123")
        for i in range(profile_view.FOLLOW_LIST_PAGE_SIZE + 2):
            follower = User.objects.create_user(
                username=f"follower{i}",
                email=f"f{i}@example.org",
                password="Password123",
            )
            Follower.objects.create(author=self.user, follower=follower)

        ctx = profile_view._follow_context(self.user, self.user)

        self.assertEqual(len(ctx["followers_users"]), profile_view.FOLLOW_LIST_PAGE_SIZE)
        self.assertTrue(ctx["followers_has_more"])
        self.assertEqual(ctx["followers_next_page"], 2)

    def test_profile_follow_list_endpoint_returns_paginated_followers(self):
        self.client.login(username=self.user.username, password="Password123")
        for i in range(profile_view.FOLLOW_LIST_PAGE_SIZE * 2 + 1):
            follower = User.objects.create_user(
                username=f"fol{i}",
                email=f"fol{i}@example.org",
                password="Password123",
            )
            Follower.objects.create(author=self.user, follower=follower)

        url = f"{reverse('profile_follow_list')}?user={self.user.username}&list=followers&page=2"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertTrue(payload["has_more"])
        self.assertEqual(payload["next_page"], 3)
        self.assertIn("fol25", payload["html"])

    def test_profile_follow_list_endpoint_defaults_invalid_page_params(self):
        self.client.login(username=self.user.username, password="Password123")
        for i in range(profile_view.FOLLOW_LIST_PAGE_SIZE + 1):
            follower = User.objects.create_user(
                username=f"err{i}",
                email=f"err{i}@example.org",
                password="Password123",
            )
            Follower.objects.create(author=self.user, follower=follower)

        url = f"{reverse('profile_follow_list')}?user={self.user.username}&list=followers&page=bad&page_size=oops"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["has_more"])
        self.assertEqual(payload["next_page"], 2)
        self.assertIn("err0", payload["html"])

    def test_profile_follow_list_endpoint_returns_following(self):
        self.client.login(username=self.user.username, password="Password123")
        for i in range(3):
            author = User.objects.create_user(
                username=f"auth{i}",
                email=f"a{i}@example.org",
                password="Password123",
            )
            Follower.objects.create(follower=self.user, author=author)

        url = f"{reverse('profile_follow_list')}?user={self.user.username}&list=following"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertIn("auth1", payload["html"])
        self.assertFalse(payload["has_more"])
        self.assertIsNone(payload["next_page"])

    def test_profile_follow_list_endpoint_respects_privacy(self):
        private_user = User.objects.get(username='@janedoe')
        private_user.is_private = True
        private_user.save()
        viewer = User.objects.create_user(username="@viewerz", email="vz@example.org", password="Password123")
        self.client.login(username=viewer.username, password="Password123")

        url = f"{reverse('profile_follow_list')}?user={private_user.username}&list=followers"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_profile_follow_list_unknown_list_returns_400(self):
        self.client.login(username=self.user.username, password="Password123")
        url = f"{reverse('profile_follow_list')}?user={self.user.username}&list=bogus"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_profile_follow_list_close_friends_requires_owner(self):
        other = User.objects.get(username='@janedoe')
        self.client.login(username=self.user.username, password="Password123")
        url = f"{reverse('profile_follow_list')}?user={other.username}&list=close_friends"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_profile_follow_list_close_friends_returns_items_for_owner(self):
        self.client.login(username=self.user.username, password="Password123")
        follower = User.objects.create_user(username="@cf", email="cf@example.org", password="Password123")
        Follower.objects.create(author=self.user, follower=follower)
        url = f"{reverse('profile_follow_list')}?user={self.user.username}&list=close_friends"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("html", payload)
        self.assertIn("@cf", payload["html"])
