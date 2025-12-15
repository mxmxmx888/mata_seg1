from django.test import TestCase, RequestFactory
from recipes.adapters import CustomAccountAdapter
from recipes.models import User

class CustomAdapterTests(TestCase):
    def setUp(self):
        User.objects.filter(username__startswith="test").delete()
        self.adapter = CustomAccountAdapter()

    def test_populate_username_uses_existing(self):
        user = User(username="validuser", email="test@test.com")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "validuser")

    def test_populate_username_from_email(self):
        user = User(username="", email="bob@example.com")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "bob")

    def test_populate_username_from_firstname(self):
        user = User(username="", email="", first_name="Alice")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "alice")

    def test_populate_username_fallback(self):
        user = User(username="", email="")
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "user")

    def test_populate_username_handles_collisions(self):
        User.objects.create(username="test")
        user = User(username="", email="test@example.com")
        
        result = self.adapter.populate_username(None, user)
        self.assertEqual(result, "test1")