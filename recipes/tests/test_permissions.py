from types import SimpleNamespace

from django.test import SimpleTestCase

from recipes.permissions import IsOwnerOrReadOnly


class IsOwnerOrReadOnlyTests(SimpleTestCase):
    def setUp(self):
        self.permission = IsOwnerOrReadOnly()
        # Use distinct objects so identity checks are clear
        self.owner = object()
        self.other_user = object()
        self.view = object()

    def _make_request(self, method: str, user) -> SimpleNamespace:
        return SimpleNamespace(method=method, user=user)

    def test_safe_methods_are_allowed_for_any_user(self):
        """GET / HEAD / OPTIONS should always be allowed."""
        obj = SimpleNamespace(author=self.other_user)

        for method in ("GET", "HEAD", "OPTIONS"):
            with self.subTest(method=method):
                request = self._make_request(method, self.owner)
                self.assertTrue(
                    self.permission.has_object_permission(request, self.view, obj)
                )

    def test_unsafe_methods_allowed_for_owner(self):
        """Non-safe methods allowed when request.user is the author."""
        obj = SimpleNamespace(author=self.owner)
        request = self._make_request("PUT", self.owner)

        self.assertTrue(
            self.permission.has_object_permission(request, self.view, obj)
        )

    def test_unsafe_methods_denied_for_non_owner(self):
        """Non-safe methods denied when request.user is not the author."""
        obj = SimpleNamespace(author=self.other_user)
        request = self._make_request("DELETE", self.owner)

        self.assertFalse(
            self.permission.has_object_permission(request, self.view, obj)
        )
