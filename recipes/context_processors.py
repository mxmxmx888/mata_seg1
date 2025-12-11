from recipes.models import Notification

def notifications(request):
    if request.user.is_authenticated:
        notifs = Notification.objects.filter(recipient=request.user).select_related('sender', 'post')[:10]
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {
            'notifications': notifs,
            'unread_notifications_count': unread_count
        }
    return {}