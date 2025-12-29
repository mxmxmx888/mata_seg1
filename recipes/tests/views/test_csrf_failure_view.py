from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from recipes.views.csrf_failure_view import csrf_debug_failure


class CSRFDebugFailureTests(TestCase):
    def test_logs_tokens_and_returns_forbidden_response(self):
        request = RequestFactory().post("/some-path/", data={"csrfmiddlewaretoken": "posttoken"})
        request.COOKIES[settings.CSRF_COOKIE_NAME] = "cookietoken"
        request.META["HTTP_X_CSRFTOKEN"] = "headertoken"
        request.user = AnonymousUser()

        with self.assertLogs("recipes.views.csrf_failure_view", level="WARNING") as logs:
            response = csrf_debug_failure(request, reason="bad")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(any("bad" in entry and "cookietoken" in entry and "posttoken" in entry and "headertoken" in entry for entry in logs.output))
