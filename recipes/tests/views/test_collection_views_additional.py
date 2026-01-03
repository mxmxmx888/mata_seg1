from unittest.mock import patch, MagicMock
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser

from recipes.views import collection_views


class CollectionViewsAdditionalTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_update_collection_blank_redirects(self):
        request = self.factory.post("/collections/", {"title": " "})
        request.user = type("U", (), {"is_authenticated": True})()
        fav = MagicMock(id="fav", name="Old")
        with patch.object(collection_views, "favourite_service") as svc:
            svc.fetch_for_user.return_value = fav
            response = collection_views.update_collection(request, "fav")
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("collection_detail", kwargs={"slug": "fav"}), response.url)

    def test_collection_payload_fields(self):
        fav = MagicMock(id="1", name="Name")
        payload = collection_views._collection_payload(fav, ["p"])
        self.assertEqual(payload["id"], "1")
        self.assertEqual(payload["items"], ["p"])
