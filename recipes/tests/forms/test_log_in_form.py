"""Unit tests of the log in form."""
from unittest.mock import patch

from django import forms
from django.test import TestCase

from recipes.forms import LogInForm
from recipes.models import User

class LogInFormTestCase(TestCase):
    """Unit tests of the log in form."""

    fixtures = ['recipes/tests/fixtures/default_user.json']

    def setUp(self):
        self.form_input = {'username': '@janedoe', 'password': 'Password123'}

    def test_form_contains_required_fields(self):
        form = LogInForm()
        self.assertIn('username', form.fields)
        self.assertIn('password', form.fields)
        password_field = form.fields['password']
        self.assertTrue(isinstance(password_field.widget,forms.PasswordInput))

    def test_form_accepts_valid_input(self):
        form = LogInForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_form_rejects_blank_username(self):
        self.form_input['username'] = ''
        form = LogInForm(data=self.form_input)
        self.assertFalse(form.is_valid())

    def test_form_rejects_blank_password(self):
        self.form_input['password'] = ''
        form = LogInForm(data=self.form_input)
        self.assertFalse(form.is_valid())

    def test_form_accepts_incorrect_username(self):
        self.form_input['username'] = 'ja'
        form = LogInForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_form_accepts_incorrect_password(self):
        self.form_input['password'] = 'pwd'
        form = LogInForm(data=self.form_input)
        self.assertTrue(form.is_valid())

    def test_can_authenticate_valid_user(self):
        fixture = User.objects.get(username='@johndoe')
        form_input = {'username': '@johndoe', 'password': 'Password123'}
        form = LogInForm(data=form_input)
        user = form.get_user()
        self.assertEqual(user, fixture)

    def test_invalid_credentials_do_not_authenticate(self):
        form_input = {'username': '@johndoe', 'password': 'WrongPassword123'}
        form = LogInForm(data=form_input)
        user = form.get_user()
        self.assertEqual(user, None)

    def test_blank_password_does_not_authenticate(self):
        form_input = {'username': '@johndoe', 'password': ''}
        form = LogInForm(data=form_input)
        user = form.get_user()
        self.assertEqual(user, None)

    def test_blank_username_does_not_authenticate(self):
        form_input = {'username': '', 'password': 'Password123'}
        form = LogInForm(data=form_input)
        user = form.get_user()
        self.assertEqual(user, None)

    def test_returns_none_when_missing_credentials_after_validation(self):
        form = LogInForm(data={"username": "", "password": ""})
        form.cleaned_data = {"username": "", "password": ""}
        with patch.object(form, "is_valid", return_value=True):
            user = form.get_user()
        self.assertIsNone(user)

    @patch("recipes.forms.log_in_form._is_running_tests", return_value=False)
    def test_logs_and_returns_none_when_user_missing_outside_tests(self, _):
        form = LogInForm(data={"username": "@missing", "password": "Password123"})
        with patch("builtins.print") as print_mock:
            user = form.get_user()
        self.assertIsNone(user)
        print_mock.assert_called_once()

    @patch("recipes.forms.log_in_form._is_running_tests", return_value=True)
    def test_returns_none_when_user_missing_in_tests(self, _):
        form = LogInForm(data={"username": "@missing", "password": "Password123"})
        user = form.get_user()
        self.assertIsNone(user)

    @patch("recipes.forms.log_in_form.authenticate")
    @patch("recipes.forms.log_in_form.sign_in_with_email_and_password")
    def test_get_user_prefers_firebase_result(self, mock_sign_in, mock_authenticate):
        mock_sign_in.return_value = {"uid": "abc"}
        mock_authenticate.return_value = None

        form = LogInForm(data={"username": "@johndoe", "password": "Password123"})
        user = form.get_user()

        mock_sign_in.assert_called_once_with(
            email="johndoe@example.org",
            password="Password123",
        )
        mock_authenticate.assert_not_called()
        self.assertEqual(user.username, "@johndoe")
        self.assertEqual(user.backend, "django.contrib.auth.backends.ModelBackend")

    @patch("recipes.forms.log_in_form._is_running_tests", return_value=False)
    @patch("recipes.forms.log_in_form.authenticate")
    @patch("recipes.forms.log_in_form.sign_in_with_email_and_password")
    def test_get_user_logs_when_firebase_succeeds_outside_tests(self, mock_sign_in, mock_authenticate, _):
        mock_sign_in.return_value = {"uid": "abc"}
        mock_authenticate.return_value = None

        form = LogInForm(data={"username": "@johndoe", "password": "Password123"})
        with patch("builtins.print") as print_mock:
            user = form.get_user()

        self.assertEqual(user.username, "@johndoe")
        self.assertEqual(user.backend, "django.contrib.auth.backends.ModelBackend")
        self.assertEqual(print_mock.call_count, 2)
        mock_authenticate.assert_not_called()

    @patch("recipes.forms.log_in_form.authenticate")
    @patch("recipes.forms.log_in_form.sign_in_with_email_and_password")
    def test_get_user_falls_back_to_authenticate(self, mock_sign_in, mock_authenticate):
        mock_sign_in.return_value = None
        fallback_user = User.objects.get(username="@johndoe")
        mock_authenticate.return_value = fallback_user

        form = LogInForm(data={"username": "@johndoe", "password": "Password123"})
        user = form.get_user()

        mock_sign_in.assert_called_once()
        mock_authenticate.assert_called_once_with(
            username="@johndoe",
            password="Password123",
        )
        self.assertEqual(user, fallback_user)

    @patch("recipes.forms.log_in_form._is_running_tests", return_value=False)
    @patch("recipes.forms.log_in_form.authenticate")
    @patch("recipes.forms.log_in_form.sign_in_with_email_and_password")
    def test_get_user_logs_fallback_authenticate_outside_tests(self, mock_sign_in, mock_authenticate, _):
        mock_sign_in.return_value = None
        fallback_user = User.objects.get(username="@johndoe")
        mock_authenticate.return_value = fallback_user

        form = LogInForm(data={"username": "@johndoe", "password": "Password123"})
        with patch("builtins.print") as print_mock:
            user = form.get_user()

        self.assertEqual(user, fallback_user)
        self.assertEqual(print_mock.call_count, 2)
        mock_sign_in.assert_called_once()
        mock_authenticate.assert_called_once_with(username="@johndoe", password="Password123")
