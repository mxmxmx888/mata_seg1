"""Profile page views and helpers for rendering user profiles and follow lists."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from recipes.forms import PasswordForm, UserForm
from recipes.repos.post_repo import PostRepo
from recipes.repos.user_repo import UserRepo
from recipes.models.follow_request import FollowRequest
from recipes.models.close_friend import CloseFriend
from recipes.services import PrivacyService
from recipes.services import FollowService
from recipes.models import Follower, Favourite, RecipePost
from recipes.models.favourite_item import FavouriteItem
from recipes.views.profile_data_helpers import profile_data_for_user, collections_for_user

User = get_user_model()
post_repo = PostRepo()
user_repo = UserRepo()
privacy_service = PrivacyService()
follow_service_factory = FollowService
_profile_data_for_user = profile_data_for_user
_collections_for_user = collections_for_user
FOLLOW_LIST_PAGE_SIZE = 25


def _paginate_follow_queryset(qs, user_attr, page_size=FOLLOW_LIST_PAGE_SIZE, page_number=1):
    """Return total, page of related users, and pagination flags for a follow queryset."""
    total = qs.count()
    start = (max(1, page_number) - 1) * page_size
    end = start + page_size
    users = [getattr(relation, user_attr) for relation in qs[start:end]]
    has_more = total > end
    next_page = page_number + 1 if has_more else None
    return total, users, has_more, next_page


def _follow_context(profile_user, viewer):
    """Gather follow relationships and visibility for profile page."""
    followers_qs = Follower.objects.filter(author=profile_user).select_related("follower")
    following_qs = Follower.objects.filter(follower=profile_user).select_related("author")

    followers_count, followers_users, followers_has_more, followers_next_page = _paginate_follow_queryset(
        followers_qs, "follower"
    )
    following_count, following_users, following_has_more, following_next_page = _paginate_follow_queryset(
        following_qs, "author"
    )

    close_friend_ids = set(
        CloseFriend.objects.filter(owner=profile_user).values_list("friend_id", flat=True)
    )
    close_friends = [
        follower
        for follower in followers_users
        if follower.id in close_friend_ids
    ]

    is_following = _is_following_profile(viewer, profile_user)
    pending_request = _pending_follow_request(viewer, profile_user, is_following)
    can_view_follow_lists = _can_view_follow_lists(profile_user, viewer, is_following)
    if not can_view_follow_lists:
        followers_users = []
        following_users = []
        followers_has_more = False
        followers_next_page = None
        following_has_more = False
        following_next_page = None

    return {
        "followers_count": followers_count,
        "following_count": following_count,
        "followers_users": followers_users,
        "following_users": following_users,
        "close_friend_ids": close_friend_ids,
        "close_friends": close_friends,
        "followers_has_more": followers_has_more,
        "followers_next_page": followers_next_page,
        "following_has_more": following_has_more,
        "following_next_page": following_next_page,
        "is_following": is_following,
        "pending_request": pending_request,
        "can_view_follow_lists": can_view_follow_lists,
        "close_friends_has_more": followers_has_more if can_view_follow_lists else False,
        "close_friends_next_page": followers_next_page if can_view_follow_lists else None,
    }


def _handle_profile_post(request, profile_user):
    """Process profile POST actions (cancel request, update profile)."""
    if request.POST.get("cancel_request") == "1":
        service = follow_service_factory(request.user)
        service.cancel_request(profile_user)
        return redirect(request.get_full_path()), None, None, None

    if profile_user != request.user:
        return redirect("profile"), None, None, None

    form = UserForm(request.POST, request.FILES, instance=request.user)
    edit_profile_form = form
    show_modal = True
    if form.is_valid():
        changed_fields = set(form.changed_data)

        if changed_fields:
            form.save()

            non_avatar_changes = changed_fields - {"avatar", "remove_avatar"}
            if non_avatar_changes:
                messages.add_message(request, messages.SUCCESS, "Profile updated!")

        request.session["show_edit_profile_modal"] = True
        return redirect("profile"), form, edit_profile_form, show_modal

    # keep bound form with errors
    return None, form, edit_profile_form, show_modal


def _profile_user_from_request(request):
    """Resolve which profile to show based on ?user= param or the requester."""
    username = request.GET.get("user")
    if username:
        try:
            return user_repo.get_by_username(username)
        except User.DoesNotExist:
            raise Http404("User not found")  # pragma: no cover - surface-level 404
    return request.user


def _is_following_profile(viewer, profile_user):
    """Return True when viewer already follows the profile_user."""
    if profile_user == viewer:
        return False
    return Follower.objects.filter(
        follower=viewer,
        author=profile_user,
    ).exists()


def _pending_follow_request(viewer, profile_user, is_following):
    """Return pending FollowRequest for viewer→profile_user if applicable."""
    if profile_user == viewer or is_following or not getattr(profile_user, "is_private", False):
        return None
    return FollowRequest.objects.filter(
        requester=viewer,
        target=profile_user,
        status=FollowRequest.STATUS_PENDING,
    ).first()


def _can_view_follow_lists(profile_user, viewer, is_following):
    """Check whether viewer is allowed to see followers/following lists."""
    return (
        profile_user == viewer
        or not getattr(profile_user, "is_private", False)
        or is_following
    )


def _profile_posts(profile_user, viewer):
    """Return (posts_qs, can_view_profile) respecting privacy (queryset, not list)."""
    can_view_profile = privacy_service.can_view_profile(viewer, profile_user)
    if not can_view_profile:
        # Viewer cannot see this profile; return an empty posts queryset.
        return RecipePost.objects.none(), can_view_profile

    posts_qs = post_repo.list_for_user(
        profile_user.id,
        order_by=("-created_at",),
    )
    if profile_user != viewer:
        posts_qs = privacy_service.filter_visible_posts(posts_qs, viewer)
    return posts_qs, can_view_profile


def _profile_forms(request, profile_user, is_own_profile):
    """Initialise forms and handle POST updates; returns (redirect_response, form, edit_form, password_form, show_modal)."""
    edit_profile_form = UserForm(instance=request.user)
    password_form = PasswordForm(user=request.user)
    show_edit_profile_modal = request.session.pop("show_edit_profile_modal", False)

    if request.method != "POST":
        form = UserForm(instance=request.user) if is_own_profile else None
        return None, form, edit_profile_form, password_form, show_edit_profile_modal

    redirect_response, form, edit_profile_form, show_edit_profile_modal = _handle_profile_post(
        request, profile_user
    )
    return redirect_response, form, edit_profile_form, password_form, show_edit_profile_modal


def _profile_context(
    profile_user,
    viewer,
    is_own_profile,
    follow_ctx,
    profile_data,
    form,
    edit_profile_form,
    password_form,
    posts,
    collections,
    can_view_profile,
    show_edit_profile_modal,
):
    """Build the context dict for profile rendering."""
    return {
        "profile": profile_data,
        "collections": collections,
        "form": form,
        "edit_profile_form": edit_profile_form,
        "password_form": password_form,
        "profile_user": profile_user,
        "is_own_profile": is_own_profile,
        "is_following": follow_ctx["is_following"],
        "followers_count": follow_ctx["followers_count"],
        "following_count": follow_ctx["following_count"],
        "followers_users": follow_ctx["followers_users"],
        "following_users": follow_ctx["following_users"],
        "close_friends": follow_ctx["close_friends"],
        "posts": posts,
        "can_view_profile": can_view_profile,
        "can_view_follow_lists": follow_ctx["can_view_follow_lists"],
        "followers_has_more": follow_ctx["followers_has_more"],
        "followers_next_page": follow_ctx["followers_next_page"],
        "following_has_more": follow_ctx["following_has_more"],
        "following_next_page": follow_ctx["following_next_page"],
        "close_friends_has_more": follow_ctx["close_friends_has_more"],
        "close_friends_next_page": follow_ctx["close_friends_next_page"],
        "pending_follow_request": follow_ctx["pending_request"],
        "close_friend_ids": follow_ctx["close_friend_ids"],
        "show_edit_profile_modal": show_edit_profile_modal,
    }


@login_required
def profile_follow_list(request):
    """Return paginated followers/following/close friend candidates as HTML chunks."""
    profile_user = _profile_user_from_request(request)
    is_own_profile = profile_user == request.user
    list_type = request.GET.get("list")
    page_number = max(1, int(request.GET.get("page") or 1))

    follow_ctx = _follow_context(profile_user, request.user)
    if not follow_ctx["can_view_follow_lists"]:
        return JsonResponse({"error": "Not allowed"}, status=403)

    if list_type == "followers":
        qs = Follower.objects.filter(author=profile_user).select_related("follower")
        user_attr = "follower"
        template = "partials/profile/follow_list_items.html"
    elif list_type == "following":
        qs = Follower.objects.filter(follower=profile_user).select_related("author")
        user_attr = "author"
        template = "partials/profile/follow_list_items.html"
    elif list_type == "close_friends":
        if not is_own_profile:
            return JsonResponse({"error": "Not allowed"}, status=403)
        qs = Follower.objects.filter(author=profile_user).select_related("follower")
        user_attr = "follower"
        template = "partials/profile/close_friend_items.html"
    else:
        return JsonResponse({"error": "Unknown list"}, status=400)

    total, users, has_more, next_page = _paginate_follow_queryset(
        qs, user_attr, page_number=page_number
    )
    context = {
        "users": users,
        "list_type": list_type,
        "is_own_profile": is_own_profile,
        "close_friend_ids": follow_ctx["close_friend_ids"],
    }
    html = render_to_string(template, context, request=request)
    return JsonResponse({"html": html, "has_more": has_more, "next_page": next_page, "total": total})


@login_required
def profile(request):
    """Render the profile page for the requested user (or self)."""
    profile_user = _profile_user_from_request(request)
    is_own_profile = profile_user == request.user

    follow_ctx = _follow_context(profile_user, request.user)
    profile_data = profile_data_for_user(profile_user)
    profile_data["followers"] = follow_ctx["followers_count"]
    profile_data["following"] = follow_ctx["following_count"]
    profile_data["close_friends_count"] = len(follow_ctx["close_friend_ids"])

    redirect_response, form, edit_profile_form, password_form, show_edit_profile_modal = _profile_forms(
        request, profile_user, is_own_profile
    )
    if redirect_response:
        return redirect_response

    page_size = 12
    page_number = max(1, int(request.GET.get("page") or 1))
    posts_qs, can_view_profile = _profile_posts(profile_user, request.user)
    start = (page_number - 1) * page_size
    end = start + page_size
    posts_page = list(posts_qs[start:end]) if can_view_profile else []
    posts_has_more = posts_qs.count() > end if can_view_profile else False

    if request.headers.get("HX-Request") and request.GET.get("posts_only") == "1":
        return render(
            request,
            "partials/feed/feed_cards.html",
            {"posts": posts_page, "request": request},
        )

    collections = collections_for_user(profile_user)

    context = _profile_context(
        profile_user,
        request.user,
        is_own_profile,
        follow_ctx,
        profile_data,
        form,
        edit_profile_form,
        password_form,
        posts_page,
        collections,
        can_view_profile,
        show_edit_profile_modal,
    )
    context.update(
        {
            "posts_has_more": posts_has_more,
            "posts_next_page": page_number + 1 if posts_has_more else None,
        }
    )

    return render(request, "profile/profile.html", context)
