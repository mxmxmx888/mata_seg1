"""Model for user-submitted reports against posts or comments."""

import uuid
from django.db import models
from django.conf import settings
from .recipe_post import RecipePost
from .comment import Comment

class Report(models.Model):
    """User-submitted report against a recipe or comment."""
    REPORT_REASONS = [
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('harassment', 'Harassment'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Who is reporting?
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='submitted_reports'
    )
    
    recipe_post = models.ForeignKey(
        RecipePost, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='reports'
    )
    comment = models.ForeignKey(
        Comment, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='reports'
    )
    
    reason = models.CharField(max_length=50, choices=REPORT_REASONS)
    description = models.TextField(blank=True, help_text="Additional details from the user")
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False, help_text="Has an admin dealt with this?")
    resolution_note = models.TextField(blank=True, help_text="Admin's notes on the decision")

    class Meta:
        """Ordering and table name for reports."""
        db_table = 'report'
        ordering = ['-created_at']

    def __str__(self):
        """Readable summary of the report target and reporter."""
        target = "Recipe" if self.recipe_post else "Comment"
        return f"Report on {target} by {self.reporter.username}"
