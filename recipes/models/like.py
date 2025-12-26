"""Model representing a user's like on a recipe post."""

from django.db import models
from .user import User
from .recipe_post import RecipePost

class Like(models.Model):
    """User like on a recipe post."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='likes'
    )

    recipe_post = models.ForeignKey(
        RecipePost,
        on_delete=models.CASCADE,
        db_column='recipe_post_id',
        related_name='likes'
    )

    class Meta:
        """Enforce one like per user/post pair."""
        # Composite PK is simulated using unique_together
        unique_together = (
            ('user', 'recipe_post'),
        )

        db_table = "like"

    def __str__(self):
        """Readable representation for admin/debugging."""
        return f"{self.user_id} → {self.recipe_post_id}"
