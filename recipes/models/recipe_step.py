"""Model representing an individual recipe step with ordering."""

from django.db import models
from .recipe_post import RecipePost

class RecipeStep(models.Model):
    """Ordered instruction step for a recipe post."""
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
        """Uniqueness and ordering constraints for steps."""
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
        """Readable snippet of the step for admin/debugging."""
        return f"Step {self.position}: {self.description[:30]}..."
