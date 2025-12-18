from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from recipes.models.comment import Comment
from recipes.models.report import Report
from recipes.tests.helpers import make_user, make_recipe_post


class ReportModelTests(TestCase):
    def setUp(self):
        self.reporter = make_user(username="@reporter")
        self.author = make_user(username="@author")
        self.recipe_post = make_recipe_post(author=self.author, title="Hello")

    def test_str_for_recipe_report(self):
        report = Report.objects.create(
            reporter=self.reporter,
            recipe_post=self.recipe_post,
            reason="spam",
        )
        self.assertEqual(str(report), f"Report on Recipe by {self.reporter.username}")

    def test_str_for_comment_report(self):
        comment = Comment.objects.create(
            recipe_post=self.recipe_post,
            user=self.author,
            text="Nice",
        )
        report = Report.objects.create(
            reporter=self.reporter,
            comment=comment,
            reason="harassment",
        )
        self.assertEqual(str(report), f"Report on Comment by {self.reporter.username}")

    def test_default_flags_and_ordering_newest_first(self):
        older = Report.objects.create(
            reporter=self.reporter,
            recipe_post=self.recipe_post,
            reason="spam",
        )
        newer = Report.objects.create(
            reporter=self.reporter,
            recipe_post=self.recipe_post,
            reason="other",
        )
        older.created_at = timezone.now() - timedelta(days=1)
        older.save(update_fields=["created_at"])

        reports = list(Report.objects.all())
        self.assertEqual(reports[0].id, newer.id)
        self.assertEqual(reports[1].id, older.id)
        self.assertFalse(older.is_resolved)
        self.assertFalse(newer.is_resolved)
