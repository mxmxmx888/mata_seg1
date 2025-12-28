from unittest.mock import patch, MagicMock
from django.test import TestCase

import os
import recipes.firebase_admin_client as client


class FirebaseAdminClientTests(TestCase):

    def tearDown(self):
        client._app = None  

    def test_is_mock_handles_exception(self):
        with patch("recipes.firebase_admin_client.type", side_effect=Exception("boom")):
            self.assertFalse(client._is_mock(object()))

    @patch("firebase_admin._apps", {})
    def test_get_app_blocks_during_tests_without_mocks(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=True), \
             patch("recipes.firebase_admin_client._is_mock", return_value=False), \
             patch.dict(os.environ, {}, clear=True):
            result = client.get_app()
            self.assertIsNone(result)



    @patch("firebase_admin._apps", {})
    def test_get_app_returns_none_when_missing_env(self):
        with patch.dict(os.environ, {}, clear=True):
            result = client.get_app()
            self.assertIsNone(result)

    @patch("firebase_admin._apps", {})
    def test_get_app_env_exists_but_missing_file(self):
        with patch.dict(os.environ, {"FIREBASE_SERVICE_ACCOUNT_FILE": "/missing/file"}, clear=True), \
             patch("os.path.exists", return_value=False):
            result = client.get_app()
            self.assertIsNone(result)

    @patch("firebase_admin._apps", {})
    def test_get_app_initializes_when_valid(self):
        cred_mock = MagicMock()
        init_mock = MagicMock(return_value="APPX")

        with patch.dict(os.environ, {"FIREBASE_SERVICE_ACCOUNT_FILE": "/works.json"}, clear=True), \
             patch("os.path.exists", return_value=True), \
             patch("firebase_admin.credentials.Certificate", return_value=cred_mock), \
             patch("firebase_admin.initialize_app", init_mock):
            result = client.get_app()
            self.assertEqual(result, "APPX")
            again = client.get_app()
            self.assertEqual(again, "APPX")

    @patch("firebase_admin._apps", {})
    def test_get_app_initialization_failure(self):
        with patch.dict(os.environ, {"FIREBASE_SERVICE_ACCOUNT_FILE": "/works.json"}, clear=True), \
             patch("os.path.exists", return_value=True), \
             patch("firebase_admin.credentials.Certificate", side_effect=Exception("boom")):
            result = client.get_app()
            self.assertIsNone(result)

    def test_get_app_returns_existing_when_already_initialised(self):
        with patch("firebase_admin._apps", {"default": "X"}), \
             patch("firebase_admin.get_app", return_value="EXISTING"):
            result = client.get_app()
            self.assertEqual(result, "EXISTING")

    @patch("firebase_admin._apps", {})
    def test_get_app_logs_missing_credentials_outside_tests(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False), \
             patch.dict(os.environ, {}, clear=True), \
             patch("builtins.print") as print_mock:
            result = client.get_app()
            self.assertIsNone(result)
            print_mock.assert_called_once()

    @patch("firebase_admin._apps", {})
    def test_get_app_logs_initialization_error_outside_tests(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False), \
             patch.dict(os.environ, {"FIREBASE_SERVICE_ACCOUNT_FILE": "/works.json"}, clear=True), \
             patch("os.path.exists", return_value=True), \
             patch("firebase_admin.credentials.Certificate", return_value="CRED"), \
             patch("firebase_admin.initialize_app", side_effect=Exception("boom")), \
             patch("builtins.print") as print_mock:
            result = client.get_app()
            self.assertIsNone(result)
            print_mock.assert_called_once()

    @patch("firebase_admin._apps", {})
    def test_get_app_suppresses_logs_for_missing_creds_during_tests(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=True), \
             patch.dict(os.environ, {"FIREBASE_ALLOW_TEST_APP": "true"}, clear=True):
            result = client.get_app()
            self.assertIsNone(result)

    @patch("firebase_admin._apps", {})
    def test_get_app_suppresses_logs_for_init_failure_during_tests(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=True), \
             patch.dict(os.environ, {
                 "FIREBASE_ALLOW_TEST_APP": "true",
                 "FIREBASE_SERVICE_ACCOUNT_FILE": "/works.json",
             }, clear=True), \
             patch("os.path.exists", return_value=True), \
             patch("firebase_admin.credentials.Certificate", return_value="CRED"), \
             patch("firebase_admin.initialize_app", side_effect=Exception("boom")):
            result = client.get_app()
            self.assertIsNone(result)

    

    def test_firestore_returns_none_when_tests_running(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=True):
            result = client.get_firestore_client()
            self.assertIsNone(result)

    def test_firestore_returns_none_when_no_app(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False), \
             patch("recipes.firebase_admin_client.get_app", return_value=None):
            result = client.get_firestore_client()
            self.assertIsNone(result)

    def test_firestore_respects_env_flag(self):
        with patch.dict(os.environ, {"FIREBASE_ENABLE_FIRESTORE": "false"}, clear=True):
            result = client.get_firestore_client()
            self.assertIsNone(result)

    def test_firestore_returns_client(self):
        mock_client = MagicMock()
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False), \
             patch("recipes.firebase_admin_client.get_app", return_value="APP"), \
             patch("recipes.firebase_admin_client.firestore.client", return_value=mock_client):
            result = client.get_firestore_client()
            self.assertEqual(result, mock_client)

   

    def test_ensure_none_when_no_email(self):
        self.assertIsNone(client.ensure_firebase_user(""))

    def test_ensure_none_when_app_unavailable(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False), \
             patch("recipes.firebase_admin_client.get_app", return_value=None):
            result = client.ensure_firebase_user("x@test.com")
            self.assertIsNone(result)

    def test_ensure_none_when_app_unavailable_in_tests_without_mocks(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=True), \
             patch("recipes.firebase_admin_client._is_mock", return_value=False):
            result = client.ensure_firebase_user("x@test.com")
            self.assertIsNone(result)

    def test_ensure_none_when_app_unavailable_default_path(self):
        with patch("recipes.firebase_admin_client.get_app", return_value=None):
            result = client.ensure_firebase_user("x@test.com")
            self.assertIsNone(result)

    def test_ensure_get_user_success(self):
        with patch("recipes.firebase_admin_client.get_app", return_value="APP"), \
             patch("recipes.firebase_admin_client.auth.get_user_by_email", return_value="USR"):
            result = client.ensure_firebase_user("x@test.com")
            self.assertEqual(result, "USR")

    def test_ensure_user_not_found_creates(self):
        with patch("recipes.firebase_admin_client.get_app", return_value="APP"), \
             patch("recipes.firebase_admin_client.auth.get_user_by_email",
                   side_effect=client.auth.UserNotFoundError("no user")), \
             patch("recipes.firebase_admin_client.auth.create_user", return_value="NEWU"):
            result = client.ensure_firebase_user("x@test.com")
            self.assertEqual(result, "NEWU")

    def test_ensure_create_user_exception(self):
        with patch("recipes.firebase_admin_client.get_app", return_value="APP"), \
             patch("recipes.firebase_admin_client.auth.get_user_by_email",
                   side_effect=client.auth.UserNotFoundError("no user")), \
             patch("recipes.firebase_admin_client.auth.create_user",
                   side_effect=Exception("boom")):
            result = client.ensure_firebase_user("x@test.com")
            self.assertIsNone(result)

    def test_ensure_create_user_exception_logs_outside_tests(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False), \
             patch("recipes.firebase_admin_client.get_app", return_value=True), \
             patch("recipes.firebase_admin_client.auth.get_user_by_email",
                   side_effect=client.auth.UserNotFoundError("no user")), \
             patch("recipes.firebase_admin_client.auth.create_user",
                   side_effect=Exception("boom")), \
             patch("builtins.print") as print_mock:
            result = client.ensure_firebase_user("x@test.com", "Name")
            self.assertIsNone(result)
            print_mock.assert_called_once()

    def test_ensure_general_exception(self):
        with patch("recipes.firebase_admin_client.get_app", return_value="APP"), \
             patch("recipes.firebase_admin_client.auth.get_user_by_email",
                   side_effect=Exception("x")):
            result = client.ensure_firebase_user("z@test.com")
            self.assertIsNone(result)

    def test_ensure_general_exception_logs_outside_tests(self):
        with patch("recipes.firebase_admin_client._is_running_tests", return_value=False), \
             patch("recipes.firebase_admin_client.get_app", return_value=True), \
             patch("recipes.firebase_admin_client.auth.get_user_by_email",
                   side_effect=Exception("fail")), \
             patch("builtins.print") as print_mock:
            result = client.ensure_firebase_user("z@test.com")
            self.assertIsNone(result)
            print_mock.assert_called_once()
