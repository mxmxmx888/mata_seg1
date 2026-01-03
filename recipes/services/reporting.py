"""Service helpers for reporting recipes or comments."""

from django.shortcuts import get_object_or_404
from recipes.models.recipe_post import RecipePost
from recipes.models.comment import Comment


class ReportingService:
    """Encapsulate report target lookup and report persistence."""

    def fetch_recipe(self, object_id):
        return get_object_or_404(RecipePost, id=object_id)

    def fetch_comment(self, object_id):
        return get_object_or_404(Comment, id=object_id)

    def report_for(self, content_type, object_id):
        if content_type == "recipe":
            return self.fetch_recipe(object_id), None
        if content_type == "comment":
            return None, self.fetch_comment(object_id)
        return None, None

    def save_report(self, form, reporter, *, recipe=None, comment=None):
        report = form.save(commit=False)
        report.reporter = reporter
        report.recipe_post = recipe
        report.comment = comment
        report.save()
        return report
