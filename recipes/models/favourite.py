import uuid
from django.conf import settings
from django.db import models


class Favourite(models.Model):
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
