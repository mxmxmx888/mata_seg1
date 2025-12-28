import os
from django.test import TestCase
from unittest.mock import patch, MagicMock
from recipes import firebase_admin_client, firebase_auth_services


class FirebaseAdminClientTests(TestCase):
    def tearDown(self):
        firebase_admin_client._app = None


    @patch("recipes.firebase_admin_client.firebase_admin.get_app")
    @patch("recipes.firebase_admin_client.firebase_admin._apps", [1])
    def test_get_app_returns_existing(self, mock_get_app):
        mock_get_app.return_value = "APP"
        app = firebase_admin_client.get_app()
        self.assertEqual(app, "APP")


    @patch("recipes.firebase_admin_client.os.path.exists", return_value=True)
    @patch.dict(os.environ, {"FIREBASE_SERVICE_ACCOUNT_FILE": "/tmp/test.json"})
    @patch("recipes.firebase_admin_client.credentials.Certificate")
    @patch("recipes.firebase_admin_client.firebase_admin.initialize_app")
    @patch("recipes.firebase_admin_client.firebase_admin._apps", {})
    def test_get_app_initializes_new(self, mock_init, mock_cert, *_):
        app = firebase_admin_client.get_app()
        mock_init.assert_called()
        self.assertIsNotNone(app)


    @patch("recipes.firebase_admin_client.auth.get_user_by_email")
    def test_ensure_firebase_user_skips_if_exists(self, mock_get):
        firebase_admin_client.ensure_firebase_user("e@test.com")
        mock_get.assert_called_once()

 
    @patch("recipes.firebase_admin_client.auth.create_user")
    @patch("recipes.firebase_admin_client.auth.get_user_by_email")
    def test_ensure_firebase_user_creates_when_missing(self, mock_get, mock_create):
        class NotFound(Exception): ...
        firebase_admin_client.auth.UserNotFoundError = NotFound
        mock_get.side_effect = NotFound()
        
        firebase_admin_client.ensure_firebase_user("e@test.com", display_name="u")
        
        mock_create.assert_called_once_with(email="e@test.com", display_name="u")


    @patch("recipes.firebase_admin_client.auth.get_user_by_email")
    def test_ensure_firebase_user_handles_exception(self, mock_get):
        mock_get.side_effect = Exception("boom")

        try:
            firebase_admin_client.ensure_firebase_user("a@test.com")
        except Exception:
            self.fail("ensure_firebase_user() should swallow exceptions")


class FirebaseAuthServicesTests(TestCase):

    def test_sign_in_skips_network_when_tests_and_not_mocked(self):
        def dummy_post(*_, **__):
            return None
        dummy_post.__module__ = "recipes.tests.dummy"

        with patch("recipes.firebase_auth_services._is_running_tests", return_value=True):
            with patch("recipes.firebase_auth_services.requests.post", dummy_post):
                res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
                self.assertIsNone(res)

    def test_sign_in_handles_mock_detection_exception(self):
        def dummy_post(*_, **__):
            return None
        dummy_post.__module__ = "recipes.tests.dummy"

        with patch("recipes.firebase_auth_services._is_running_tests", return_value=True), \
             patch("recipes.firebase_auth_services.type", side_effect=Exception("boom")), \
             patch("recipes.firebase_auth_services.requests.post", dummy_post):
            res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
            self.assertIsNone(res)

    def test_sign_in_missing_api_key_logs(self):
        with patch("recipes.firebase_auth_services._is_running_tests", return_value=False), \
             patch("recipes.firebase_auth_services.settings", create=True) as mock_settings, \
             patch("builtins.print") as print_mock:
            mock_settings.FIREBASE_API_KEY = None
            res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
            self.assertIsNone(res)
            print_mock.assert_called_once()

    def test_sign_in_missing_api_key_skips_logs_in_tests(self):
        with patch("recipes.firebase_auth_services._is_running_tests", return_value=True), \
             patch("recipes.firebase_auth_services.requests.post", MagicMock(name="post")), \
             patch("recipes.firebase_auth_services.settings", create=True) as mock_settings, \
             patch("builtins.print") as print_mock:
            mock_settings.FIREBASE_API_KEY = None
            res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
            self.assertIsNone(res)
            print_mock.assert_not_called()

    @patch("recipes.firebase_auth_services.requests.post")
    def test_sign_in_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"token": "abc"}
        res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
        self.assertEqual(res["token"], "abc")

    @patch("recipes.firebase_auth_services.requests.post")
    def test_sign_in_failure_returns_none(self, mock_post):
        mock_post.return_value.status_code = 400
        res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
        self.assertIsNone(res)

    def test_sign_in_success_logs_outside_tests(self):
        class DummyResponse:
            status_code = 200
            def json(self):
                return {"ok": True}
        with patch("recipes.firebase_auth_services._is_running_tests", return_value=False), \
             patch("recipes.firebase_auth_services.settings", create=True) as mock_settings, \
             patch("recipes.firebase_auth_services.requests.post", return_value=DummyResponse()), \
             patch("builtins.print") as print_mock:
            mock_settings.FIREBASE_API_KEY = "key"
            res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
            self.assertEqual(res, {"ok": True})
            print_mock.assert_called_once()

    def test_sign_in_failure_logs_outside_tests(self):
        class DummyResponse:
            status_code = 401
            text = "bad"
        with patch("recipes.firebase_auth_services._is_running_tests", return_value=False), \
             patch("recipes.firebase_auth_services.settings", create=True) as mock_settings, \
             patch("recipes.firebase_auth_services.requests.post", return_value=DummyResponse()), \
             patch("builtins.print") as print_mock:
            mock_settings.FIREBASE_API_KEY = "key"
            res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
            self.assertIsNone(res)
            self.assertEqual(print_mock.call_count, 3)

    @patch("recipes.firebase_auth_services.firebase_auth.create_user")
    def test_create_user(self, mock_create):
        firebase_auth_services.create_firebase_user("uid", "e", "p")
        mock_create.assert_called_with(uid="uid", email="e", password="p")

    @patch("recipes.firebase_auth_services.firebase_auth.generate_password_reset_link")
    def test_reset_link_success(self, mock_gen):
        mock_gen.return_value = "LINK"
        res = firebase_auth_services.generate_password_reset_link("e@test.com")
        self.assertEqual(res, "LINK")

    @patch("recipes.firebase_auth_services.firebase_auth.generate_password_reset_link")
    def test_reset_link_failure_returns_none(self, mock_gen):
        mock_gen.side_effect = Exception("fail")
        res = firebase_auth_services.generate_password_reset_link("e@test.com")
        self.assertIsNone(res)

    def test_reset_link_failure_logs_outside_tests(self):
        with patch("recipes.firebase_auth_services.firebase_auth.generate_password_reset_link",
                   side_effect=Exception("fail")), \
             patch("recipes.firebase_auth_services._is_running_tests", return_value=False), \
             patch("builtins.print") as print_mock:
            res = firebase_auth_services.generate_password_reset_link("e@test.com")
            self.assertIsNone(res)
            print_mock.assert_called_once()

    def test_reset_link_user_not_found_logs_outside_tests(self):
        class NotFound(Exception): ...
        with patch("recipes.firebase_auth_services.firebase_auth.generate_password_reset_link",
                   side_effect=NotFound()), \
             patch("recipes.firebase_auth_services._is_running_tests", return_value=False), \
             patch("builtins.print") as print_mock:
            firebase_auth_services.firebase_auth.UserNotFoundError = NotFound
            res = firebase_auth_services.generate_password_reset_link("e@test.com")
            self.assertIsNone(res)
            print_mock.assert_called_once()

    def test_reset_link_user_not_found_suppresses_log_in_tests(self):
        class NotFound(Exception): ...
        with patch("recipes.firebase_auth_services.firebase_auth.generate_password_reset_link",
                   side_effect=NotFound()), \
             patch("recipes.firebase_auth_services._is_running_tests", return_value=True), \
             patch("builtins.print") as print_mock:
            firebase_auth_services.firebase_auth.UserNotFoundError = NotFound
            res = firebase_auth_services.generate_password_reset_link("e@test.com")
            self.assertIsNone(res)
            print_mock.assert_not_called()
