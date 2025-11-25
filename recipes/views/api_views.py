from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


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
