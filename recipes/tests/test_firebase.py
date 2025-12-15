import os
from django.test import TestCase
from unittest.mock import patch, MagicMock
from recipes import firebase_admin_client, firebase_auth_services

class FirebaseClientTests(TestCase):
    def tearDown(self):
        firebase_admin_client._app = None

    @patch('recipes.firebase_admin_client.firebase_admin.get_app')
    def test_get_app_existing(self, mock_get):
        mock_get.return_value = "App"
        with patch('recipes.firebase_admin_client.firebase_admin._apps', [1]):
            self.assertEqual(firebase_admin_client.get_app(), "App")

    @patch('recipes.firebase_admin_client.credentials.Certificate')
    @patch('recipes.firebase_admin_client.firebase_admin.initialize_app')
    def test_get_app_initializes(self, mock_init, mock_cert):
        with patch('recipes.firebase_admin_client.firebase_admin._apps', {}):
            with patch.dict('os.environ', {'FIREBASE_SERVICE_ACCOUNT_FILE': 'path'}):
                with patch('os.path.exists', return_value=True):
                    app = firebase_admin_client.get_app()
                    mock_init.assert_called()
                    self.assertIsNotNone(app)

    @patch('recipes.firebase_admin_client.auth')
    def test_ensure_firebase_user_creates(self, mock_auth):
        mock_auth.UserNotFoundError = Exception
        mock_auth.get_user_by_email.side_effect = mock_auth.UserNotFoundError
        firebase_admin_client.ensure_firebase_user("e@test.com")
        mock_auth.create_user.assert_called_with(
            email="e@test.com", display_name=None
        )

class FirebaseAuthServicesTests(TestCase):
    @patch('recipes.firebase_auth_services.requests.post')
    def test_sign_in_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'id': 1}
        with patch('django.conf.settings.FIREBASE_API_KEY', 'key'):
            res = firebase_auth_services.sign_in_with_email_and_password("u", "p")
            self.assertEqual(res['id'], 1)

    @patch('recipes.firebase_auth_services.firebase_auth.create_user')
    def test_create_firebase_user(self, mock_create):
        with patch('recipes.firebase_auth_services.get_app'):
            firebase_auth_services.create_firebase_user("uid", "e", "p")
            mock_create.assert_called_with(uid="uid", email="e", password="p")

    @patch('recipes.firebase_auth_services.firebase_auth.generate_password_reset_link')
    def test_gen_reset_link_success(self, mock_gen):
        mock_gen.return_value = "link"
        with patch('recipes.firebase_auth_services.get_app'):
            res = firebase_auth_services.generate_password_reset_link("e")
            self.assertEqual(res, "link")