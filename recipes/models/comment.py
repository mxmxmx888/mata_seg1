import uuid
from django.db import models
from .user import User
from .recipe_post import RecipePost

"""
Comment model

This table stores comments that users leave on recipe posts.

Each row represents one comment:
- `recipe_post` points to the RecipePost being commented on.
- `user` points to the User who wrote the comment.
- `text` holds the comment content (up to 2000 characters).
- `created_at` records when the comment was created.
- `is_hidden` lets admins hide a comment (e.g. after reports) without deleting it.

The `__str__` method is just for readable debugging/admin display.
"""

class Comment(models.Model):
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
        db_table = "comment"

    def __str__(self):
        return f"Comment by {self.user_id} on {self.recipe_post_id}"
    