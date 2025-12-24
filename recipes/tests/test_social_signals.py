from unittest.mock import patch, MagicMock
from django.test import TestCase
from google.api_core.exceptions import NotFound
from recipes.models import User
from recipes import social_signals

class SocialSignalsTestCase(TestCase):
    fixtures = ["recipes/tests/fixtures/default_user.json"]

    def setUp(self):
        self.user = User.objects.get(username="@johndoe")
        self.user.first_name = "John"
        social_signals._firestore_unavailable = False

    def test_social_signal_syncs_user(self):
        sociallogin = type("SL", (), {"user": self.user})
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)
        sync.assert_called_once_with(email=self.user.email, display_name=self.user.get_full_name())

    def test_social_signal_returns_when_no_user(self):
        sociallogin = type("SL", (), {"user": None})
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)
        sync.assert_not_called()

    def test_social_signal_skips_without_email(self):
        self.user.email = ""
        sociallogin = type("SL", (), {"user": self.user})
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)
        self.assertFalse(sync.called)

    def test_social_signal_uses_username_when_full_name_missing(self):
        self.user.first_name = ""
        self.user.last_name = ""
        sociallogin = type("SL", (), {"user": self.user})
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)
        sync.assert_called_once_with(email=self.user.email, display_name=self.user.username)

    def test_social_signal_uses_email_when_no_get_full_name_attr(self):
        simple_user = type("SimpleUser", (), {"username": "u1", "email": "x@example.com"})()
        sociallogin = type("SL", (), {"user": simple_user})
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)
        sync.assert_called_once_with(email="x@example.com", display_name="u1")

    def test_social_signal_handles_exception(self):
        sociallogin = type("SL", (), {"user": self.user})
        with patch.object(social_signals, "ensure_firebase_user", side_effect=RuntimeError("boom")):
            social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)

    def test_social_signal_logs_exception_when_logging_enabled(self):
        sociallogin = type("SL", (), {"user": self.user})
        with patch.object(social_signals, "_should_log", return_value=True):
            with patch.object(social_signals, "ensure_firebase_user", side_effect=RuntimeError("boom")):
                with patch.object(social_signals.logger, "warning") as log_mock:
                    social_signals.sync_google_user_to_firebase_on_social(None, None, sociallogin)
                    log_mock.assert_called_once()

    def test_login_signal_syncs_user(self):
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_user_to_firebase_on_login(None, None, self.user)
        sync.assert_called_once_with(email=self.user.email, display_name=self.user.get_full_name())

    def test_login_signal_uses_username_when_full_name_missing(self):
        self.user.first_name = ""
        self.user.last_name = ""
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_user_to_firebase_on_login(None, None, self.user)
        sync.assert_called_once_with(email=self.user.email, display_name=self.user.username)

    def test_login_signal_uses_username_when_no_get_full_name_attr(self):
        simple_user = type("SimpleUser", (), {"username": "u1", "email": "x@example.com"})()
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_user_to_firebase_on_login(None, None, simple_user)
        sync.assert_called_once_with(email="x@example.com", display_name="u1")

    def test_login_signal_skips_when_no_email(self):
        self.user.email = ""
        with patch.object(social_signals, "ensure_firebase_user") as sync:
            social_signals.sync_user_to_firebase_on_login(None, None, self.user)
        self.assertFalse(sync.called)

    def test_login_signal_handles_exception(self):
        with patch.object(social_signals, "ensure_firebase_user", side_effect=RuntimeError("x")):
            social_signals.sync_user_to_firebase_on_login(None, None, self.user)

    def test_login_signal_logs_exception_when_logging_enabled(self):
        with patch.object(social_signals, "_should_log", return_value=True):
            with patch.object(social_signals, "ensure_firebase_user", side_effect=RuntimeError("x")):
                with patch.object(social_signals.logger, "warning") as log_mock:
                    social_signals.sync_user_to_firebase_on_login(None, None, self.user)
                    log_mock.assert_called_once()

    def test_sync_user_data_to_firestore_skips_when_no_client(self):
        with patch.object(social_signals, "get_firestore_client", return_value=None):
            social_signals.sync_user_data_to_firestore(User, self.user, created=False)

    def test_sync_user_data_to_firestore_sets_document(self):
        mock_db = MagicMock()
        mock_doc = mock_db.collection.return_value.document.return_value
        with patch.object(social_signals, "get_firestore_client", return_value=mock_db):
            social_signals.sync_user_data_to_firestore(User, self.user, created=False)

        mock_db.collection.assert_called_once_with("users")
        mock_db.collection.return_value.document.assert_called_once_with(str(self.user.id))
        mock_doc.set.assert_called_once()

    def test_sync_user_data_to_firestore_logs_errors_when_enabled(self):
        with patch.object(social_signals, "get_firestore_client") as get_client:
            mock_db = MagicMock()
            mock_db.collection.return_value.document.return_value.set.side_effect = RuntimeError("fail")
            get_client.return_value = mock_db
            with patch.object(social_signals, "_should_log", return_value=True):
                with patch.object(social_signals.logger, "warning") as log_mock:
                    social_signals.sync_user_data_to_firestore(User, self.user, created=False)
                    log_mock.assert_called_once()

    def test_sync_user_data_to_firestore_suppresses_log_when_disabled(self):
        with patch.object(social_signals, "get_firestore_client") as get_client:
            mock_db = MagicMock()
            mock_db.collection.return_value.document.return_value.set.side_effect = RuntimeError("fail")
            get_client.return_value = mock_db
            with patch.object(social_signals, "_should_log", return_value=False):
                with patch.object(social_signals.logger, "warning") as log_mock:
                    social_signals.sync_user_data_to_firestore(User, self.user, created=False)
                    log_mock.assert_not_called()

    def test_sync_user_data_to_firestore_disables_after_missing_db(self):
        with patch.object(social_signals, "get_firestore_client") as get_client:
            mock_db = MagicMock()
            mock_db.collection.return_value.document.return_value.set.side_effect = NotFound("no db")
            get_client.return_value = mock_db
            with patch.object(social_signals, "_should_log", return_value=True):
                with patch.object(social_signals.logger, "warning") as log_mock:
                    social_signals.sync_user_data_to_firestore(User, self.user, created=False)
                    self.assertTrue(social_signals._firestore_unavailable)
                    log_mock.assert_called_once()

        # Once disabled, it should short-circuit without hitting Firestore
        mock_db.collection.assert_called_once()  # first call
        social_signals.sync_user_data_to_firestore(User, self.user, created=False)
        mock_db.collection.assert_called_once()
