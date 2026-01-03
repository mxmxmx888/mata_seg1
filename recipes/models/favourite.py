"""Model for a user's named collection of saved recipe posts."""

import uuid
from django.conf import settings
from django.db import models

class Favourite(models.Model):
    """A collection of saved recipe posts for a user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favourites",
    )

    name = models.CharField(max_length=255)

    cover_post = models.ForeignKey(
        "recipes.RecipePost",
        on_delete=models.SET_NULL,
        related_name="cover_for_favourites",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """DB metadata and constraints for favourites."""
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
        """Readable label for admin/debugging."""
        return f"Favourite(user={self.user_id}, name={self.name})"
