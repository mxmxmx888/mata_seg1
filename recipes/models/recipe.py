"""Legacy recipe model with basic text fields."""

from django.conf import settings
from django.db import models


class Recipe(models.Model):
    """Legacy recipe model storing freeform ingredients/method."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    ingredients = models.TextField()  # you can store one ingredient per line
    method = models.TextField()
    category = models.CharField(max_length=50, blank=True)
    cook_time_minutes = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    rating_sum = models.PositiveIntegerField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    favourites_count = models.PositiveIntegerField(default=0)

    class Meta:
        """Default ordering for legacy recipes."""
        ordering = ["-created_at"]

    def __str__(self):
        """Readable representation for admin/debugging."""
        return self.title

    def average_rating(self):
        """Compute average rating from sum/count."""
        if self.rating_count == 0:
            return 0
        return self.rating_sum / self.rating_count
