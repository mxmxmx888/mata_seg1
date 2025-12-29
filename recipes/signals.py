import re
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from recipes.models import Like, Comment, Follower, Notification, RecipePost

User = get_user_model()

@receiver(post_save, sender=Like)
def notify_on_like(sender, instance, created, **kwargs):
    """Create a notification when a post is liked by someone else."""
    if created and instance.user != instance.recipe_post.author:
        Notification.objects.create(
            recipient=instance.recipe_post.author,
            sender=instance.user,
            notification_type='like',
            post=instance.recipe_post
        )

@receiver(post_save, sender=Follower)
def notify_on_follow(sender, instance, created, **kwargs):
    """Create a notification when a user starts following an author."""
    if created:
        Notification.objects.create(
            recipient=instance.author,
            sender=instance.follower,
            notification_type='follow'
        )

@receiver(post_save, sender=Comment)
def notify_on_comment(sender, instance, created, **kwargs):
    """Create notifications for comments and @mentions."""
    if not created:
        return
    _notify_post_author(instance)
    _notify_mentions(instance)

def _notify_post_author(comment):
    if comment.user == comment.recipe_post.author:
        return
    Notification.objects.create(
        recipient=comment.recipe_post.author,
        sender=comment.user,
        notification_type='comment',
        post=comment.recipe_post,
        comment=comment,
    )

def _notify_mentions(comment):
    for username in re.findall(r'@(\w+)', comment.text):
        tagged_user = _safe_get_user(username)
        if not tagged_user or tagged_user == comment.user:
            continue
        Notification.objects.create(
            recipient=tagged_user,
            sender=comment.user,
            notification_type='tag',
            post=comment.recipe_post,
            comment=comment,
        )

def _safe_get_user(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


@receiver(post_save, sender=Notification)
def trim_notification_history(sender, instance, created, **kwargs):
    """Keep a reasonable cap on notification history without nuking recent items."""
    if not created:
        return

    keep_ids = list(
        Notification.objects.filter(recipient=instance.recipient)
        .order_by("-created_at", "-id")
        .values_list("id", flat=True)[:100]
    )
    if keep_ids:
        Notification.objects.filter(recipient=instance.recipient).exclude(id__in=keep_ids).delete()
