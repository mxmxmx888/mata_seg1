from rest_framework import generics, filters, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from recipes.models import Notification, RecipePost
from recipes.serializers import RecipeSerializer
from recipes.permissions import IsOwnerOrReadOnly


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
    """Mark all unread notifications for the current user as read."""
    page_size = 50
    page_number = max(1, int(request.GET.get("page") or 1))
    notifications_qs = (
        Notification.objects.filter(recipient=request.user)
        .select_related("sender", "post", "follow_request")
        .order_by("-created_at", "-id")
    )
    start = (page_number - 1) * page_size
    end = start + page_size
    page_items = list(notifications_qs[start:end])
    has_more = notifications_qs.count() > end

    # mark fetched items as read
    Notification.objects.filter(id__in=[n.id for n in page_items], is_read=False).update(is_read=True)

    html = render_to_string(
        "partials/navbar/notification_items.html",
        {"notifications": page_items, "following_ids": set(), "request": request},
        request=request,
    )
    return JsonResponse({"html": html, "has_more": has_more, "next_page": page_number + 1 if has_more else None})


class RecipeListApi(generics.ListCreateAPIView):
    """List recipes for the user and allow creation."""
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'category']
    ordering_fields = ['average_rating', 'created_at']

    def get_queryset(self):
        """
        Optionally restricts the returned recipes by filtering
        against a `category` or `search` query parameter in the URL.
        """
        queryset = RecipePost.objects.all()
        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')

        if category:
            queryset = queryset.filter(category__iexact=category)
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset

    def perform_create(self, serializer):
        """Assign current user as author on create."""
        serializer.save(author=self.request.user)


class RecipeDetailApi(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a recipe, respecting ownership permissions."""
    queryset = RecipePost.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsOwnerOrReadOnly]
