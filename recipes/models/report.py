import uuid
from django.db import models
from django.conf import settings
from .recipe_post import RecipePost
from .comment import Comment

"""
Report model

This table stores user reports for moderation.

- A Report is created by a `reporter` (the user who is reporting something).
- A report can target *either* a RecipePost OR a Comment:
  - `recipe_post` is optional
  - `comment` is optional
  - In your app logic, you should ensure exactly one of them is set (not both, not neither).
- `reason` is a short category (spam / inappropriate / harassment / other).
- `description` is optional extra detail from the reporter.

Moderation workflow:
- `is_resolved` tracks whether an admin has dealt with the report.
- `resolution_note` stores admin notes/explanation.

Meta:
- Stored in DB table name `report`
- Default ordering shows newest reports first.
"""

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
        db_table = 'report'
        ordering = ['-created_at']

    def __str__(self):
        target = "Recipe" if self.recipe_post else "Comment"
        return f"Report on {target} by {self.reporter.username}"
