from django.db import models
from .user import User
from .recipe_post import RecipePost


class Like(models.Model):
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
        # Composite PK is simulated using unique_together
        unique_together = (
            ('user', 'recipe_post'),
        )

        db_table = "like"

    def __str__(self):
        return f"{self.user_id} → {self.recipe_post_id}"