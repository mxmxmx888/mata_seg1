from django.db import models
from .recipe_post import RecipePost

class RecipeStep(models.Model):
    recipe_post = models.ForeignKey(
        RecipePost,
        on_delete=models.CASCADE,
        db_column='recipe_post_id',
        related_name='steps'
    )

    # position (PK component)
    position = models.PositiveIntegerField()

    # description (1–1000 chars)
    description = models.TextField(max_length=1000)

    class Meta:
        # Composite PK simulation: enforce uniqueness at DB level
        unique_together = (
            ('recipe_post', 'position'),
        )

        constraints = [
            # position > 0
            models.CheckConstraint(
                check=models.Q(position__gt=0),
                name="recipe_step_position_gt_0"
            ),

            # description length >= 1 implicitly enforced by required field
        ]

        db_table = "recipe_step"

    def __str__(self):
        return f"Step {self.position}: {self.description[:30]}..."
