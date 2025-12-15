import uuid
from django.db import models
from .recipe_post import RecipePost


class Ingredient(models.Model):
    # Composite key part 1: recipe_post_id
    recipe_post = models.ForeignKey(
        RecipePost,
        to_field='id',
        on_delete=models.CASCADE,
        db_column='recipe_post_id',
        related_name='ingredients'
    )

    # Composite key part 2: name (normalized: lowercased before save)
    name = models.CharField(max_length=255)

    # position in the recipe
    position = models.PositiveIntegerField(default=1)
    
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    unit = models.CharField(max_length=50, null=True, blank=True)
    
    # NEW: Link to buy the product
    shop_url = models.URLField(max_length=500, blank=True, null=True, help_text="Link to buy this product online")

    shop_image_upload = models.ImageField(
        upload_to='shop_items/',
        blank=True,
        null=True,
        help_text="Custom image for this product in the Shop section",
    )

    class Meta:
        unique_together = (
            ('recipe_post', 'name'),
            ('recipe_post', 'position'),
        )
        constraints = [
            models.CheckConstraint(
                check=models.Q(position__gt=0),
                name='ingredient_position_gt_0'
            ),
        ]

    def save(self, *args, **kwargs):
        # normalize name: case-insensitive
        if self.name:
            self.name = self.name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.quantity or ''} {self.unit or ''})"