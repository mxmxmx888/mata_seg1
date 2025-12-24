import uuid
from django.conf import settings
from django.db import models

"""
Favourite model

This table represents a user's “collection” of saved recipe posts.

Examples:
- "favourites"
- "dinner ideas"
- "meal prep"

Key points:
- Each Favourite belongs to exactly one user.
- `name` is the label for the collection and must be unique per user
  (so the same user can’t have two collections both called "favourites",
  but different users can).
- `cover_post` is optional and lets you pin a specific RecipePost as the
  collection cover image/preview. If that post gets deleted, Django sets
  this field to NULL (it doesn't delete the collection).
- Index on `user` speeds up loading all favourites for a user.

The `__str__` method just gives a readable representation for debugging/admin.
"""

class Favourite(models.Model):
    """A collection of saved recipe posts for a user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favourites",
    )

    # collection name, e.g. "favourites", "dinner ideas"
    name = models.CharField(max_length=255)

    # optional explicit cover recipe for this collection
    cover_post = models.ForeignKey(
        "recipes.RecipePost",
        on_delete=models.SET_NULL,
        related_name="cover_for_favourites",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favourite"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="uniq_favourite_user_name",
            ),
        ]
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"Favourite(user={self.user_id}, name={self.name})"
