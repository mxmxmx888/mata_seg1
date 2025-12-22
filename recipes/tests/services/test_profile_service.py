from django.test import TestCase

from recipes.services.profile import ProfileDisplayService
from recipes.tests.helpers import make_user


class ProfileDisplayServiceTests(TestCase):
    def test_user_avatar_returns_empty_for_anonymous(self):
        svc = ProfileDisplayService(user=None)
        self.assertEqual(svc.navbar_avatar_url(), "")
        self.assertEqual(svc.editing_avatar_url(), "")

    def test_user_avatar_returns_avatar_url_when_authenticated(self):
        user = type("U", (), {"is_authenticated": True, "avatar_url": "http://example.com/avatar.jpg"})()
        svc = ProfileDisplayService(user=user)
        self.assertEqual(svc.navbar_avatar_url(), "http://example.com/avatar.jpg")
        self.assertEqual(svc.editing_avatar_url(), "http://example.com/avatar.jpg")
