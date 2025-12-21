import re
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


from recipes.adapters import CustomAccountAdapter


class CustomAccountAdapterTests(TestCase):

    def setUp(self):
        self.adapter = CustomAccountAdapter()
        self.User = get_user_model()



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
