import uuid
from django.db import models
from django.utils import timezone
from .user import User


class RecipePost(models.Model):
    # Primary key: UUIDv7 simulated using uuid.uuid4 (closest available)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Foreign key to User (uuid v7 → user.id)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipe_posts',
        db_column='author_id'
    )

    # Basic fields
    title = models.CharField(max_length=255)   # required
    description = models.TextField(max_length=4000)  # 1–4000 chars
    image = models.CharField(max_length=500, blank=True, null=True)

    # Time fields
    prep_time_min = models.PositiveIntegerField(default=0)
    cook_time_min = models.PositiveIntegerField(default=0)

    # tags: stored as JSON (string array)
    tags = models.JSONField(default=list, blank=True)

    # nutrition summary (free text or JSON string)
    nutrition = models.TextField(blank=True, null=True)
    
    # category (breakfast, lunch, etc.)
    category = models.TextField(blank=True, null= True)

    # saved count
    saved_count = models.PositiveIntegerField(default=0)

    # Timestamps
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recipe_post'

    def __str__(self):
        return self.title