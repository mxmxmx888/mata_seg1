import uuid
from django.db import models
from django.utils import timezone
from .user import User
from django.db import models
from django.conf import settings

"""
RecipePost + RecipeImage models

These two tables represent recipes and their images.

RecipePost:
- Stores the main “post” a user publishes: title, description, timings, tags, etc.
- `author` links the post to the user who created it.
- `visibility` controls who can see the post (public / followers / close friends).
- `image` is an optional “legacy/cover” image URL/path stored as a string.
- `saved_count` is a cached counter for how many times the post was saved.
- `published_at/created_at/updated_at` track lifecycle times.
- `is_hidden` lets admins hide content without deleting it.

RecipeImage:
- Stores extra images for a RecipePost using a proper ImageField.
- A post can have multiple images via `related_name="images"`.
- `position` allows ordering (0,1,2,...) so you can control image sequence.
- The Meta ordering sorts by position first, then created time, then id.

`RecipePost.primary_image_url`:
- Convenience property that chooses the “best” image to show:
  1) if the post has any RecipeImage objects, return the first image’s URL
  2) otherwise fall back to the string `image` field
  3) otherwise return None
- The try/except handles cases where an ImageField exists but has no usable URL.
"""

class RecipePost(models.Model):
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_FOLLOWERS = "followers"
    VISIBILITY_CLOSE_FRIENDS = "close_friends"

    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, "Public"),
        (VISIBILITY_FOLLOWERS, "Followers only"),
        (VISIBILITY_CLOSE_FRIENDS, "Close friends only"),
    ]
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
    serves = models.PositiveIntegerField(default=0)

    # tags: stored as JSON (string array)
    tags = models.JSONField(default=list, blank=True)

    # nutrition summary (free text or JSON string)
    nutrition = models.TextField(blank=True, null=True)
    
    # category (breakfast, lunch, etc.)
    category = models.TextField(blank=True, null= True)

    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
    )

    # saved count
    saved_count = models.PositiveIntegerField(default=0)

    # Timestamps
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_hidden = models.BooleanField(default = False, help_text = "Hidden by admin due to reports")

    class Meta:
        db_table = 'recipe_post'

    def __str__(self):
        return self.title

    @property
    def primary_image_url(self):
        images_qs = getattr(self, "images", None)
        if images_qs is not None:
            first = images_qs.first()
            if first and first.image:
                try:
                    return first.image.url
                except ValueError:
                    pass
        if self.image:
            return self.image
        return None
    
    @property
    def likes_count(self):
        return self.likes.count()




class RecipeImage(models.Model):
    recipe_post = models.ForeignKey(
        RecipePost,
        related_name="images",
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to="recipes/")
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at", "id"]

    def __str__(self):
        return f"Image for {self.recipe_post_id}"
