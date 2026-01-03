from django.test import RequestFactory, TestCase
from django.contrib.auth.models import AnonymousUser
from unittest.mock import patch

from recipes.views import report_view


class ReportViewAdditionalTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_report_target_invalid_type(self):
        recipe, comment = report_view._get_report_target("invalid", "id")
        self.assertIsNone(recipe)
        self.assertIsNone(comment)

    def test_post_invalid_form_returns_form(self):
        request = self.factory.post("/report/")
        request.user = AnonymousUser()
        with patch.object(report_view.ReportForm, "is_valid", return_value=False):
            redirect_response, form = report_view._handle_report_post(request, None, None)
        self.assertIsNone(redirect_response)
        self.assertIsNotNone(form)
