from unittest.mock import patch, MagicMock
from django.test import TestCase

import os
import recipes.firebase_admin_client as client


class FirebaseAdminClientTests(TestCase):

    def tearDown(self):
        client._app = None  # reset global between tests

    # ------------------------- get_app tests -----------------------------

    @patch("firebase_admin._apps", {})
    def test_get_app_returns_none_when_missing_env(self):
        with patch.dict(os.environ, {}, clear=True):
            result = client.get_app()
            self.assertIsNone(result)

    @patch("firebase_admin._apps", {})
    def test_get_app_env_exists_but_missing_file(self):
        with patch.dict(os.environ, {"FIREBASE_SERVICE_ACCOUNT_FILE": "/missing/file"}, clear=True):
            with patch("os.path.exists", return_value=False):
                result = client.get_app()
                self.assertIsNone(result)

    @patch("firebase_admin._apps", {})
    def test_get_app_initializes_when_valid(self):
        cred_mock = MagicMock()
        init_mock = MagicMock(return_value="APPX")

        with patch.dict(os.environ, {"FIREBASE_SERVICE_ACCOUNT_FILE": "/works.json"}, clear=True):
            with patch("os.path.exists", return_value=True):
                with patch("firebase_admin.credentials.Certificate", return_value=cred_mock):
                    with patch("firebase_admin.initialize_app", init_mock):
                        result = client.get_app()
                        self.assertEqual(result, "APPX")

                        # second call should reuse cached
                        again = client.get_app()
                        self.assertEqual(again, "APPX")

    @patch("firebase_admin._apps", {})
    def test_get_app_initialization_failure(self):
        with patch.dict(os.environ, {"FIREBASE_SERVICE_ACCOUNT_FILE": "/works.json"}, clear=True):
            with patch("os.path.exists", return_value=True):
                with patch("firebase_admin.credentials.Certificate", side_effect=Exception("boom")):
                    result = client.get_app()
                    self.assertIsNone(result)

    def test_get_app_returns_existing_when_already_initialised(self):
        with patch("firebase_admin._apps", {"default": "X"}):
            with patch("firebase_admin.get_app", return_value="EXISTING"):
                result = client.get_app()
                self.assertEqual(result, "EXISTING")

    # ------------------------- get_firestore_client tests -----------------------------

    def test_firestore_returns_none_when_tests_running(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=True):
            result = client.get_firestore_client()
            self.assertIsNone(result)

    def test_firestore_returns_none_when_no_app(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False):
            with patch("recipes.firebase_admin_client.get_app", return_value=None):
                result = client.get_firestore_client()
                self.assertIsNone(result)

    def test_firestore_returns_client(self):
        mock_client = MagicMock()
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False):
            with patch("recipes.firebase_admin_client.get_app", return_value="APP"):
                with patch("recipes.firebase_admin_client.firestore.client", return_value=mock_client):
                    result = client.get_firestore_client()
                    self.assertEqual(result, mock_client)

    # ------------------------- ensure_firebase_user tests -----------------------------

    def test_ensure_none_when_no_email(self):
        self.assertIsNone(client.ensure_firebase_user(""))

    def test_ensure_none_when_app_unavailable(self):
        with patch("recipes.firebase_admin_client.get_app", return_value=None):
            result = client.ensure_firebase_user("x@test.com")
            self.assertIsNone(result)

    def test_ensure_get_user_success(self):
        with patch("recipes.firebase_admin_client.get_app", return_value="APP"):
            with patch("recipes.firebase_admin_client.auth.get_user_by_email", return_value="USR"):
                result = client.ensure_firebase_user("x@test.com")
                self.assertEqual(result, "USR")

    def test_ensure_user_not_found_creates(self):
        with patch("recipes.firebase_admin_client.get_app", return_value="APP"):
            with patch("recipes.firebase_admin_client.auth.get_user_by_email",
                       side_effect=client.auth.UserNotFoundError("no user")):
                with patch("recipes.firebase_admin_client.auth.create_user", return_value="NEWU"):
                    result = client.ensure_firebase_user("x@test.com")
                    self.assertEqual(result, "NEWU")

    def test_ensure_create_user_exception(self):
        with patch("recipes.firebase_admin_client.get_app", return_value="APP"):
            with patch("recipes.firebase_admin_client.auth.get_user_by_email",
                       side_effect=client.auth.UserNotFoundError("no user")):
                with patch("recipes.firebase_admin_client.auth.create_user",
                           side_effect=Exception("boom")):
                    result = client.ensure_firebase_user("x@test.com")
                    self.assertIsNone(result)

    def test_ensure_general_exception(self):
        with patch("recipes.firebase_admin_client.get_app", return_value="APP"):
            with patch("recipes.firebase_admin_client.auth.get_user_by_email",
                       side_effect=Exception("x")):
                result = client.ensure_firebase_user("z@test.com")
                self.assertIsNone(result)