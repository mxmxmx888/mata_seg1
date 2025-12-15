from django.db import models
from .user import User
from .recipe_post import RecipePost

"""
Like model

This table represents a “like” that a user gives to a recipe post.

Each row means:
- one specific User liked one specific RecipePost.

Key rules:
- A user can only like the same post once.
  This is enforced by `unique_together = (user, recipe_post)`.

Relationships:
- `user` is the person who liked the post.
- `recipe_post` is the post being liked.

Notes:
- There is no separate UUID primary key here; instead, the pair (user, recipe_post)
  acts like a “composite primary key” by being unique.
- The `__str__` is mainly for admin/debugging: it prints "user_id → recipe_post_id".
"""

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