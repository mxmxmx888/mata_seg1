import uuid
from django.db import models
from .recipe_post import RecipePost

"""
Ingredient model

This table stores the ingredient list for a specific RecipePost.

Each row represents ONE ingredient used in ONE recipe, with optional quantity
and unit, plus optional “shop” metadata for linking/browsing ingredients in a
shop-like UI.

Key ideas:
- Ingredients belong to a RecipePost (FK).
- Ingredients are ordered inside the recipe using `position` (1, 2, 3, ...).
- Ingredient names are normalised to lowercase on save to keep them consistent.

Uniqueness rules:
- (recipe_post, name) must be unique:
  You can’t list “garlic” twice in the same recipe (even if typed differently).
- (recipe_post, position) must be unique:
  You can’t have two ingredients with the same position in the same recipe.

Validation / constraints:
- `position` must be > 0 (no zero/negative ordering).

Shop fields (optional):
- `shop_url` can link to an online product page.
- `shop_image_upload` stores a custom product image for the shop section.

The `__str__` output is meant to be human-friendly in admin/debug logs.
"""


class Ingredient(models.Model):
    # Composite key part 1: recipe_post_id
    recipe_post = models.ForeignKey(
        RecipePost,
        to_field='id',
        on_delete=models.CASCADE,
        db_column='recipe_post_id',
        related_name='ingredients'
    )

    # Composite key part 2: name 
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