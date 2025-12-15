from django.db import models
from django.conf import settings
from .recipe_post import RecipePost
from .comment import Comment

"""
Notification model

This table stores in-app notifications for users (the “bell” / activity feed).

Core fields:
- `recipient`: who receives the notification (the user being notified)
- `sender`: who triggered the notification (the user who did the action)
- `notification_type`: what kind of event it is (like/comment/follow/follow_request/tag)

Optional links (only filled when relevant):
- `post`: the RecipePost involved (likes/comments usually)
- `comment`: the Comment involved (comment notifications)
- `follow_request`: the FollowRequest involved (follow_request notifications)

State + ordering:
- `is_read`: whether the recipient has opened/seen it
- `created_at`: when it happened
- Notifications are ordered newest-first because of `ordering = ['-created_at']`

Notes:
- This model does not enforce “type must match fields” (e.g. type='comment' must have comment filled).
  That’s usually handled in the code that creates notifications (or with extra constraints if you want).
- `__str__` is a debug/admin-friendly summary.
"""

class Notification(models.Model):
    TYPES = [
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
        ('follow_request', 'Follow Request'),
        ('tag', 'Tag'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=TYPES)
    post = models.ForeignKey(RecipePost, null=True, blank=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE)
    follow_request = models.ForeignKey(
        "recipes.FollowRequest",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient}: {self.notification_type}"
