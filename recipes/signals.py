import re
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from recipes.models import Like, Comment, Follower, Notification, RecipePost

User = get_user_model()

@receiver(post_save, sender=Like)
def notify_on_like(sender, instance, created, **kwargs):
    if created and instance.user != instance.recipe_post.author:
        Notification.objects.create(
            recipient=instance.recipe_post.author,
            sender=instance.user,
            notification_type='like',
            post=instance.recipe_post
        )

@receiver(post_save, sender=Follower)
def notify_on_follow(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            recipient=instance.author,
            sender=instance.follower,
            notification_type='follow'
        )

@receiver(post_save, sender=Comment)
def notify_on_comment(sender, instance, created, **kwargs):
    if created:
        if instance.user != instance.recipe_post.author:
            Notification.objects.create(
                recipient=instance.recipe_post.author,
                sender=instance.user,
                notification_type='comment',
                post=instance.recipe_post,
                comment=instance
            )
        
        mentions = re.findall(r'@(\w+)', instance.text)
        for username in mentions:
            try:
                tagged_user = User.objects.get(username=username)
                if tagged_user != instance.user:
                    Notification.objects.create(
                        recipient=tagged_user,
                        sender=instance.user,
                        notification_type='tag',
                        post=instance.recipe_post,
                        comment=instance
                    )
            except User.DoesNotExist:
                continue