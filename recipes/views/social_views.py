from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from recipes.models import Follower
from recipes.models.close_friend import CloseFriend
from recipes.views.view_utils import is_ajax_request

User = get_user_model()


@login_required
@require_POST
def remove_follower(request, username):
    """Remove a follower from the current user; supports AJAX and redirect responses."""
    target = get_object_or_404(User, username=username)
    if target == request.user:
        if is_ajax_request(request):
            return JsonResponse({"error": "Cannot remove yourself"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    Follower.objects.filter(author=request.user, follower=target).delete()
    CloseFriend.objects.filter(owner=request.user, friend=target).delete()
    if is_ajax_request(request):
        return JsonResponse({"status": "removed", "follower": target.username})
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))


@login_required
@require_POST
def remove_following(request, username):
    """Unfollow a user; supports AJAX and redirect responses."""
    target = get_object_or_404(User, username=username)
    if target == request.user:
        if is_ajax_request(request):
            return JsonResponse({"error": "Cannot unfollow yourself"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    Follower.objects.filter(follower=request.user, author=target).delete()
    if is_ajax_request(request):
        return JsonResponse({"status": "removed", "following": target.username})
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))


@login_required
@require_POST
def add_close_friend(request, username):
    """Add a followed user to the current user's close friends."""
    friend = get_object_or_404(User, username=username)
    if friend == request.user:
        if is_ajax_request(request):
            return JsonResponse({"error": "Cannot add yourself"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    if not Follower.objects.filter(author=request.user, follower=friend).exists():
        if is_ajax_request(request):
            return JsonResponse({"error": "Must follow user first"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    CloseFriend.objects.get_or_create(owner=request.user, friend=friend)
    if is_ajax_request(request):
        return JsonResponse({"status": "added", "friend": friend.username})
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))


@login_required
@require_POST
def remove_close_friend(request, username):
    """Remove a user from the current user's close friends."""
    friend = get_object_or_404(User, username=username)
    if friend == request.user:
        if is_ajax_request(request):
            return JsonResponse({"error": "Cannot remove yourself"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    CloseFriend.objects.filter(owner=request.user, friend=friend).delete()
    if is_ajax_request(request):
        return JsonResponse({"status": "removed", "friend": friend.username})
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
