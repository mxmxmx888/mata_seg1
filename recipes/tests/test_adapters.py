import re
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from recipes.adapters import (
    CustomAccountAdapter,
    CustomSocialAccountAdapter,
    _unique_username,
)
from django.db import IntegrityError


class DummyQS:
    def __init__(self, exists_sequence):
        self._seq = list(exists_sequence)

    def exclude(self, pk=None):
        return self

    def exists(self):
        return self._seq.pop(0)


class DummyManager:
    def __init__(self):
        self.calls = []

    def filter(self, username):
        self.calls.append(username)
        if username == "dup":
            return DummyQS([True])
        return DummyQS([False])


class CustomAccountAdapterTests(TestCase):

    def setUp(self):
        self.adapter = CustomAccountAdapter()
        self.User = get_user_model()

    def test_unique_username_excludes_provided_user(self):
        user = self.User.objects.create_user(
            username="taken",
            email="taken@example.com",
            password="pass",
        )
        result = _unique_username("taken", self.User, exclude_user_id=user.pk)
        self.assertEqual(result, "taken")

    def test_unique_username_skips_excluded_and_increments_for_others(self):
        dummy_model = SimpleNamespace(objects=DummyManager())
        result = _unique_username("dup", dummy_model, exclude_user_id=1)
        self.assertEqual(result, "dup1")

    def test_unique_username_defaults_to_user_when_empty(self):
        result = _unique_username("", self.User)
        self.assertEqual(result, "user")

    def test_get_login_redirect_url_delegates(self):
        with patch("recipes.adapters.DefaultAccountAdapter.get_login_redirect_url", return_value="/dest") as mock:
            result = self.adapter.get_login_redirect_url(None)
            self.assertEqual(result, "/dest")
            mock.assert_called_once_with(None)


    def test_clean_username_strips_at(self):
        cleaned = self.adapter.clean_username("@john_doe")
        self.assertEqual(cleaned, "john_doe")

    def test_clean_username_allows_valid_chars(self):
        cleaned = self.adapter.clean_username("User.Name_123")
        self.assertEqual(cleaned, "User.Name_123")

    def test_clean_username_rejects_invalid_chars(self):
        with self.assertRaises(ValidationError):
            self.adapter.clean_username("bad name!")

    def test_clean_username_shallow_still_valid(self):
        cleaned = self.adapter.clean_username("hello_user", shallow=True)
        self.assertEqual(cleaned, "hello_user")



    def test_populate_username_uses_existing_username_cleaned(self):
        user = self.User(username="@Invalid!!", email="ignored@example.com")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "invalid")

    def test_populate_username_from_email(self):
        user = self.User(username="", email="First-Name+suffix@example.com")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "firstnamesuffix")

    def test_populate_username_from_first_name_if_no_email_username(self):
        user = self.User(username="", email="", first_name="John Doe")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "johndoe")

    def test_populate_username_default_fallback(self):
        user = self.User(username="", email="", first_name="")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "user")

    def test_populate_username_collision_appends_1(self):
        self.User.objects.create_user(
            username="user",
            email="existing@example.com",
            password="pass",
        )
        user = self.User(username="", email="", first_name="")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "user1")

    def test_populate_username_multiple_collisions_increment(self):
        self.User.objects.create_user(
            username="user", email="x1@example.com", password="pass"
        )
        self.User.objects.create_user(
            username="user1", email="x2@example.com", password="pass"
        )
        user = self.User(username="", email="", first_name="")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "user2")

    def test_populate_username_collision_email_based(self):
        self.User.objects.create_user(
            username="sometest", email="sometest@example.com", password="pass"
        )
        user = self.User(username="", email="some-test@example.com")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "sometest1")


class CustomSocialAccountAdapterTests(TestCase):
    def setUp(self):
        self.adapter = CustomSocialAccountAdapter()
        self.User = get_user_model()

    def test_populate_user_prefers_username_in_data(self):
        sociallogin = MagicMock()
        sociallogin.user = self.User(username="")
        data = {"username": "Cool_User", "email": "ignored@example.com"}

        user = self.adapter.populate_user(None, sociallogin, data)
        self.assertEqual(user.username, "cool_user")

    def test_populate_user_falls_back_to_name(self):
        sociallogin = MagicMock()
        sociallogin.user = self.User(username="", email="")
        data = {"name": "Name Here"}

        user = self.adapter.populate_user(None, sociallogin, data)
        self.assertEqual(user.username, "namehere")

    def test_save_user_attaches_existing_on_integrity_error(self):
        existing = self.User.objects.create_user(
            username="exists",
            email="existing@example.com",
            password="pass",
        )
        sociallogin = MagicMock()
        sociallogin.user.email = "existing@example.com"

        with patch("recipes.adapters.DefaultSocialAccountAdapter.save_user", side_effect=IntegrityError):
            user = self.adapter.save_user(None, sociallogin, form=None)

        self.assertEqual(user, existing)
        sociallogin.connect.assert_called_once_with(None, existing)

    def test_save_user_raises_when_integrity_error_and_no_email(self):
        sociallogin = MagicMock()
        sociallogin.user.email = ""

        with patch("recipes.adapters.DefaultSocialAccountAdapter.save_user", side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                self.adapter.save_user(None, sociallogin, form=None)

    def test_save_user_raises_when_integrity_error_and_no_existing(self):
        sociallogin = MagicMock()
        sociallogin.user.email = "missing@example.com"

        with patch("recipes.adapters.DefaultSocialAccountAdapter.save_user", side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                self.adapter.save_user(None, sociallogin, form=None)

    def test_save_user_success_passes_through(self):
        sociallogin = MagicMock()
        user = self.User(username="x", email="x@example.com")

        with patch("recipes.adapters.DefaultSocialAccountAdapter.save_user", return_value=user) as mock:
            result = self.adapter.save_user(None, sociallogin, form=None)

        self.assertEqual(result, user)
        mock.assert_called_once_with(None, sociallogin, form=None)
