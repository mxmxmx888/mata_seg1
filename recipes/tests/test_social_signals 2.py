from unittest.mock import patch
from django.test import TestCase
from recipes.models import User
from recipes import social_signals

class SocialSignalsTestCase(TestCase):
    fixtures = ["recipes/tests/fixtures/default_user.json"]

    def setUp(self):
        self.user = User.objects.get(username="@johndoe")
        self.user.first_name = "John"

    def test_social_signal_syncs_user(self):
        sociallogin = type("SL", (), {"user": self.user})
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)
        sync.assert_called_once_with(email=self.user.email, display_name=self.user.get_full_name())

    def test_social_signal_skips_without_email(self):
        self.user.email = ""
        sociallogin = type("SL", (), {"user": self.user})
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)
        self.assertFalse(sync.called)

    def test_social_signal_handles_exception(self):
        sociallogin = type("SL", (), {"user": self.user})
        with patch.object(social_signals, "ensure_firebase_user", side_effect=RuntimeError("boom")):
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)

    def test_login_signal_syncs_user(self):
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_user_to_firebase_on_login(None, None, self.user)
        sync.assert_called_once_with(email=self.user.email, display_name=self.user.get_full_name())

    def test_login_signal_skips_when_no_email(self):
        self.user.email = ""
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_user_to_firebase_on_login(None, None, self.user)
        self.assertFalse(sync.called)

    def test_login_signal_handles_exception(self):
        with patch.object(social_signals, "ensure_firebase_user", side_effect=RuntimeError("x")):
            social_signals.sync_user_to_firebase_on_login(None, None, self.user)
