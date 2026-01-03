"""Service helpers for creating and deleting comments."""

from django.shortcuts import get_object_or_404
from recipes.models import Comment


class CommentService:
    """Encapsulate comment CRUD for recipe posts."""

    def fetch(self, comment_id):
        """Fetch a comment by id or raise 404."""
        return get_object_or_404(Comment, id=comment_id)

    def create_comment(self, recipe, user, form):
        """Create a comment from a validated form."""
        if not form.is_valid():
            return False
        comment = form.save(commit=False)
        comment.recipe_post = recipe
        comment.user = user
        comment.save()
        return True

    def can_delete(self, comment, user):
        """Return True when the user owns the comment."""
        return comment.user == user

    def delete_comment(self, comment):
        """Delete the given comment."""
        post_id = comment.recipe_post.id
        comment.delete()
        return post_id
