import uuid
from django.db import models


class FavouriteItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    favourite = models.ForeignKey(
        "recipes.Favourite",
        on_delete=models.CASCADE,
        related_name="items",
        db_column="favourite_id",
    )

    recipe_post = models.ForeignKey(
        "recipes.RecipePost",
        on_delete=models.CASCADE,
        related_name="favourite_items",
        db_column="recipe_post_id",
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favourite_item"
        constraints = [
            models.UniqueConstraint(
                fields=["favourite", "recipe_post"],
                name="uniq_favourite_item",
            ),
        ]
        indexes = [
            models.Index(fields=["favourite"]),
            models.Index(fields=["recipe_post"]),
        ]

    def __str__(self) -> str:
        return f"FavouriteItem(favourite={self.favourite_id}, recipe_post={self.recipe_post_id})"