import uuid
from django.conf import settings
from django.db import models


class Favourite(models.Model):
    

    
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favourites",
    )
    recipe_post = models.ForeignKey(
        "recipes.RecipePost",
        on_delete=models.CASCADE,
        related_name="favourites",
    )

    class Meta:
        db_table = "favourite"
        constraints = [
            
            models.UniqueConstraint(
                fields=["user", "recipe_post"],
                name="uniq_favourite_user_recipe_post",
            ),
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["recipe_post"]),
        ]

    def __str__(self) -> str:
        return f"Favourite(user={self.user_id}, recipe_post={self.recipe_post_id})"