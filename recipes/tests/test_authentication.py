from django.test import TestCase
from rest_framework import exceptions
from unittest.mock import patch, MagicMock
from recipes.authentication import FirebaseAuthentication
from django.contrib.auth import get_user_model

User = get_user_model()

class FirebaseAuthenticationTests(TestCase):
    def setUp(self):
        self.auth = FirebaseAuthentication()
        self.request = MagicMock()
        self.user = User.objects.create_user(
            username='user1',
            email='u@e.com',
            password='password123'
        )

    @patch('recipes.authentication.auth.verify_id_token')
    def test_authenticate_success(self, mock_verify):
        self.request.META = {'HTTP_AUTHORIZATION': 'Bearer token123'}
        mock_verify.return_value = {'uid': 'user1', 'email': 'u@e.com'}
        
        user, _ = self.auth.authenticate(self.request)
        
        self.assertEqual(user, self.user)
        self.assertEqual(user.email, 'u@e.com')

    def test_authenticate_no_header(self):
        self.request.META = {}
        result = self.auth.authenticate(self.request)
        self.assertIsNone(result)

    @patch('recipes.authentication.auth.verify_id_token')
    def test_authenticate_invalid_header_format(self, mock_verify):
        mock_verify.side_effect = Exception("Invalid")
        self.request.META = {'HTTP_AUTHORIZATION': 'Basic token'}
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(self.request)

    @patch('recipes.authentication.auth.verify_id_token')
    def test_authenticate_invalid_token(self, mock_verify):
        self.request.META = {'HTTP_AUTHORIZATION': 'Bearer bad'}
        mock_verify.side_effect = Exception("Boom")
        
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.auth.authenticate(self.request)