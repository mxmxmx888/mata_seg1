from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from recipes.models.recipe_post import RecipePost

User = get_user_model()


def add_session_and_messages(request):
    """Attach session and messages storage to a RequestFactory request."""
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)
    return request


class RecipeViewTestCase(TestCase):
    """Shared setup for recipe view tests."""

    __test__ = False  # prevent Django from treating this base as a test case

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="user_a",
            email="user_a@example.org",
            password="Password123",
        )
        self.other = User.objects.create_user(
            username="user_b",
            email="user_b@example.org",
            password="Password123",
        )
        self.post = RecipePost.objects.create(
            author=self.user,
            title="Test Post",
            description="Desc",
            prep_time_min=5,
            cook_time_min=10,
            tags=["quick"],
            category="Dinner",
            visibility=RecipePost.VISIBILITY_PUBLIC,
        )
