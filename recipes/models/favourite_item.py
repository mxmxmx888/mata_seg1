import uuid
from django.db import models

"""
FavouriteItem model

This table links a user's Favourite collection to the RecipePosts saved inside it.

Think of it like a “join table”:
- A `Favourite` is a collection/list (e.g. "Dinner ideas", "Meal prep").
- A `FavouriteItem` is one saved RecipePost inside that collection.

Key points:
- Each row connects exactly one Favourite to exactly one RecipePost.
- `added_at` stores when the post was added to the collection.
- The UniqueConstraint prevents adding the same RecipePost to the same Favourite twice.
- Indexes exist to make lookups fast (e.g. fetch all items for a favourite, or find which favourites contain a post).

The `__str__` method is just for readable debugging/admin display.
"""
class FavouriteItem(models.Model):
    """Join table linking a Favourite to a RecipePost with timestamps."""
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
