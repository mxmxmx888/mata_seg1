from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from recipes.models import Notification


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_api(request):
    """
    Simple protected endpoint to test Firebase auth.
    Returns the Django user linked to the Firebase token.
    """
    user = request.user
    return Response({
        "uid": user.username,
        "email": user.email,
    })

@login_required
def mark_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})