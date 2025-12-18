from django.test import TestCase
from django.urls import reverse


class PostMockViewTests(TestCase):
    def test_mock_post_detail_renders_static_context(self):
        response = self.client.get(reverse("post_mock"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "15-minute garlic butter pasta")
        self.assertContains(response, "Garlic chili oil noodles")
