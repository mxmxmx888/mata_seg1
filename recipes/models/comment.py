"""Model for user comments on recipe posts."""

import uuid
from django.db import models
from .user import User
from .recipe_post import RecipePost

class Comment(models.Model):
    """User-authored comment on a recipe post."""
    # PK: uuid 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FK → recipe_post.id
    recipe_post = models.ForeignKey(
        RecipePost,
        on_delete=models.CASCADE,
        db_column='recipe_post_id',
        related_name='comments'
    )

    # FK → user.id
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='comments'
    )

    # text (1–2000)
    text = models.TextField(max_length=2000)

    
    created_at = models.DateTimeField(auto_now_add=True)

    is_hidden = models.BooleanField(default = False, help_text = "Hidden by admin due to reports")

    class Meta:
        """DB table name for comments."""
        db_table = "comment"

    def __str__(self):
        """Readable identifier for admin/debugging."""
        return f"Comment by {self.user_id} on {self.recipe_post_id}"
    
