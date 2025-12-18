from unittest.mock import patch
from django.urls import reverse
from django.test import TestCase
from recipes.models import User, FollowRequest, Follower

class FollowRequestViewsTestCase(TestCase):
    fixtures = [
        "recipes/tests/fixtures/default_user.json",
        "recipes/tests/fixtures/other_users.json",
    ]

    def setUp(self):
        self.firebase_patch = patch("recipes.social_signals.ensure_firebase_user", return_value=None)
        self.firebase_patch.start()
        self.target = User.objects.get(username="@johndoe")
        self.requester = User.objects.get(username="@janedoe")
        self.client.login(username=self.target.username, password="Password123")

    def tearDown(self):
        self.firebase_patch.stop()

    def test_accept_requires_post(self):
        fr = FollowRequest.objects.create(requester=self.requester, target=self.target)
        url = reverse("accept_follow_request", kwargs={"request_id": fr.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_accept_follow_request_sets_status(self):
        fr = FollowRequest.objects.create(requester=self.requester, target=self.target)
        url = reverse("accept_follow_request", kwargs={"request_id": fr.id})
        back_url = reverse("dashboard")
        response = self.client.post(url, HTTP_REFERER=back_url)
        fr.refresh_from_db()
        self.assertRedirects(response, back_url, target_status_code=200)
        self.assertEqual(fr.status, FollowRequest.STATUS_ACCEPTED)
        self.assertTrue(Follower.objects.filter(follower=self.requester, author=self.target).exists())

    def test_reject_follow_request_sets_status(self):
        fr = FollowRequest.objects.create(requester=self.requester, target=self.target)
        url = reverse("reject_follow_request", kwargs={"request_id": fr.id})
        resp = self.client.post(url)
        fr.refresh_from_db()
        self.assertRedirects(resp, reverse("dashboard"), target_status_code=200)
        self.assertEqual(fr.status, FollowRequest.STATUS_REJECTED)

    def test_reject_missing_request_redirects(self):
        url = reverse("reject_follow_request", kwargs={"request_id": "00000000-0000-0000-0000-000000000000"})
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("dashboard"), target_status_code=200)

    def test_accept_missing_request_redirects(self):
        url = reverse("accept_follow_request", kwargs={"request_id": "00000000-0000-0000-0000-000000000000"})
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("dashboard"), target_status_code=200)

    def test_get_reject_returns_forbidden(self):
        fr = FollowRequest.objects.create(requester=self.requester, target=self.target)
        url = reverse("reject_follow_request", kwargs={"request_id": fr.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
