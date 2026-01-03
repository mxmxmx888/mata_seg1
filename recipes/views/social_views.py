from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from recipes.services import FollowService
from recipes.services.users import UserService
from recipes.views.view_utils import is_ajax_request

User = get_user_model()
user_service = UserService()


def _redirect_back(request):
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))


def _self_action_error(request, message):
    if is_ajax_request(request):
        return JsonResponse({"error": message}, status=400)
    return _redirect_back(request)


@login_required
@require_POST
def remove_follower(request, username):
    """Remove a follower from the current user; supports AJAX and redirect responses."""
    target = user_service.fetch_by_username(username)
    if target == request.user:
        return _self_action_error(request, "Cannot remove yourself")

    FollowService(request.user).remove_follower(target)
    if is_ajax_request(request):
        return JsonResponse({"status": "removed", "follower": target.username})
    return _redirect_back(request)


@login_required
@require_POST
def remove_following(request, username):
    """Unfollow a user; supports AJAX and redirect responses."""
    target = user_service.fetch_by_username(username)
    if target == request.user:
        return _self_action_error(request, "Cannot unfollow yourself")

    FollowService(request.user).remove_following(target)
    if is_ajax_request(request):
        return JsonResponse({"status": "removed", "following": target.username})
    return _redirect_back(request)


@login_required
@require_POST
def add_close_friend(request, username):
    """Add a followed user to the current user's close friends."""
    friend = user_service.fetch_by_username(username)
    if friend == request.user:
        return _self_action_error(request, "Cannot add yourself")

    result = FollowService(request.user).add_close_friend(friend)
    if is_ajax_request(request):
        if result["status"] == "requires_follow":
            return JsonResponse({"error": "Must follow user first"}, status=400)
        if result["status"] != "added":
            return JsonResponse({"error": "Unable to add close friend"}, status=400)
        return JsonResponse({"status": "added", "friend": friend.username})

    return _redirect_back(request)


@login_required
@require_POST
def remove_close_friend(request, username):
    """Remove a user from the current user's close friends."""
    friend = user_service.fetch_by_username(username)
    if friend == request.user:
        return _self_action_error(request, "Cannot remove yourself")

    FollowService(request.user).remove_close_friend(friend)
    if is_ajax_request(request):
        return JsonResponse({"status": "removed", "friend": friend.username})
    return _redirect_back(request)
