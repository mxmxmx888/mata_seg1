from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from recipes.forms import PasswordForm, UserForm
from recipes.repos.post_repo import PostRepo
from recipes.repos.user_repo import UserRepo
from recipes.models.follow_request import FollowRequest
from recipes.models.close_friend import CloseFriend
from recipes.services import PrivacyService
from recipes.services import FollowService
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from recipes.models import Follower, Favourite
from recipes.models.favourite_item import FavouriteItem
from recipes.models.recipe_post import RecipePost

User = get_user_model()
post_repo = PostRepo()
user_repo = UserRepo()
privacy_service = PrivacyService()
follow_service_factory = FollowService

def _is_ajax(request):
    header = request.headers.get("HX-Request") or request.headers.get("x-requested-with")
    return bool(header == "XMLHttpRequest" or header)

def _profile_data_for_user(user):
    fallback_handle = "@anmzn"
    handle = user.username or fallback_handle
    display_name = user.get_full_name() or user.username or "cook"
    bio = getattr(user, "bio", "") or ""
    return {
        "display_name": display_name,
        "handle": handle,
        "tagline": bio,
        "following": 2,
        "followers": 0,
        "avatar_url": user.avatar_url,
        "is_private": getattr(user, "is_private", False),

    }


def _collections_for_user(user):
    """
    Build collection cards for the given user from Favourite/FavouriteItem.
    Each Favourite becomes a collection backed by the user's saved posts.
    """
    favourites = (
        Favourite.objects.filter(user=user)
        .prefetch_related("items__recipe_post")
    )

    def _post_image_url(post):
        return getattr(post, "primary_image_url", None) or getattr(post, "image", None)

    collections = []
    for fav in favourites:
        items = list(
            fav.items.select_related("recipe_post").order_by("added_at", "id")
        )
        last_saved_at = fav.created_at

        cover_post = fav.cover_post if _post_image_url(getattr(fav, "cover_post", None)) else None
        first_post_with_image = None
        visible_posts = []
        for item in items:
            if not item.recipe_post:
                continue

            visible_posts.append(item.recipe_post)
            if item.added_at and (last_saved_at is None or item.added_at > last_saved_at):
                last_saved_at = item.added_at
            if not first_post_with_image:
                image_url = _post_image_url(item.recipe_post)
                if image_url:
                    first_post_with_image = item.recipe_post

        if not cover_post:
            cover_post = first_post_with_image

        cover_url = _post_image_url(cover_post) if cover_post else None
        count = len(visible_posts)

        collections.append(
            {
                "id": str(fav.id),
                "slug": str(fav.id),
                "title": fav.name,
                "count": count,
                "privacy": None,
                "cover": cover_url,
                "has_image": bool(cover_url),
                "last_saved_at": last_saved_at,
            }
        )

    collections.sort(key=lambda c: c.get("last_saved_at"), reverse=True)

    return collections

@login_required
def profile(request):
    profile_username = request.GET.get("user")
    if profile_username:
        try:
            profile_user = user_repo.get_by_username(profile_username)
        except User.DoesNotExist:
            raise Http404("User not found")
    else:
        profile_user = request.user

    is_own_profile = profile_user == request.user

    followers_qs = Follower.objects.filter(author=profile_user).select_related("follower")
    following_qs = Follower.objects.filter(follower=profile_user).select_related("author")
    followers_count = followers_qs.count()
    following_count = following_qs.count()
    followers_users = [relation.follower for relation in followers_qs]
    following_users = [relation.author for relation in following_qs]
    close_friend_ids = set(
        CloseFriend.objects.filter(owner=profile_user).values_list("friend_id", flat=True)
    )
    close_friends = [
        relation.follower
        for relation in followers_qs
        if relation.follower_id in close_friend_ids
    ]

    is_following = False
    pending_request = None
    if not is_own_profile:
        is_following = Follower.objects.filter(
            follower=request.user,
            author=profile_user,
        ).exists()
        if not is_following and getattr(profile_user, "is_private", False):
            pending_request = FollowRequest.objects.filter(
                requester=request.user,
                target=profile_user,
                status=FollowRequest.STATUS_PENDING,
            ).first()

    profile_data = _profile_data_for_user(profile_user)
    profile_data["followers"] = followers_count
    profile_data["following"] = following_count
    profile_data["close_friends_count"] = len(close_friend_ids)

    edit_profile_form = UserForm(instance=request.user)
    password_form = PasswordForm(user=request.user)
    show_edit_profile_modal = request.session.pop("show_edit_profile_modal", False)

    if request.method == "POST":
        if request.POST.get("cancel_request") == "1":
            service = follow_service_factory(request.user)
            service.cancel_request(profile_user)
            return redirect(request.get_full_path())
        if profile_user != request.user:
            return redirect("profile")
        form = UserForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            changed_fields = set(form.changed_data)

            if changed_fields:
                form.save()

                non_avatar_changes = changed_fields - {"avatar", "remove_avatar"}
                if non_avatar_changes:
                    messages.add_message(request, messages.SUCCESS, "Profile updated!")

            request.session["show_edit_profile_modal"] = True
            return redirect("profile")
        else:
            # keep the bound form in the modal so validation errors surface
            edit_profile_form = form
            show_edit_profile_modal = True
    else:
        if profile_user == request.user:
            form = UserForm(instance=request.user)
        else:
            form = None

    can_view_profile = privacy_service.can_view_profile(request.user, profile_user)

    if can_view_profile:
        posts_qs = post_repo.list_for_user(
            profile_user.id,
            order_by=("-created_at",),
        )
        if not is_own_profile:
            posts_qs = privacy_service.filter_visible_posts(posts_qs, request.user)
        posts = list(posts_qs)
    else:
        posts = []

    collections = _collections_for_user(profile_user)

    return render(
        request,
        "profile/profile.html",
        {
        "profile": profile_data,
            "collections": collections,
            "form": form,
            "edit_profile_form": edit_profile_form,
            "password_form": password_form,
        "profile_user": profile_user,
        "is_own_profile": profile_user == request.user,
        "is_following": is_following,
            "followers_count": followers_count,
            "following_count": following_count,
            "followers_users": followers_users,
            "following_users": following_users,
            "close_friends": close_friends,
            "posts": posts,
        "can_view_profile": can_view_profile,
        "pending_follow_request": pending_request,
        "close_friend_ids": close_friend_ids,
        "show_edit_profile_modal": show_edit_profile_modal,
    },
)

@login_required
def collections_overview(request):
    context = {
        "profile": _profile_data_for_user(request.user),
        "collections": _collections_for_user(request.user),
    }
    return render(request, "app/collections.html", context)

@login_required
def collection_detail(request, slug):
    try:
        favourite = Favourite.objects.get(id=slug, user=request.user)
    except Favourite.DoesNotExist:
        raise Http404()

    items_qs = FavouriteItem.objects.filter(favourite=favourite).select_related(
        "recipe_post"
    )
    posts = []
    for item in items_qs:
        post = item.recipe_post
        if not post:
            continue
        posts.append(post)

    collection = {
        "id": str(favourite.id),
        "slug": str(favourite.id),
        "title": favourite.name,
        "description": "",
        "followers": 0,
        "items": posts,
    }

    # Distribute posts into 5 masonry columns (row-wise across the page)
    num_columns = 5
    collection_columns = [[] for _ in range(num_columns)]
    for idx, post in enumerate(posts):
        collection_columns[idx % num_columns].append(post)

    context = {
        "profile": _profile_data_for_user(request.user),
        "collection": collection,
        "posts": posts,
        "collection_columns": collection_columns,
    }
    return render(request, "app/collection_detail.html", context)


@login_required
@require_POST
def delete_collection(request, slug):
    favourite = get_object_or_404(Favourite, id=slug, user=request.user)
    favourite.delete()

    if _is_ajax(request):
        return JsonResponse({"deleted": True})

    return redirect(reverse("collections"))


@login_required
@require_POST
def update_collection(request, slug):
    favourite = get_object_or_404(Favourite, id=slug, user=request.user)
    new_title = (request.POST.get("title") or request.POST.get("name") or "").strip()

    if new_title:
        favourite.name = new_title
        favourite.save(update_fields=["name"])

    payload = {
        "id": str(favourite.id),
        "title": favourite.name,
    }
    if _is_ajax(request):
        return JsonResponse(payload)

    return redirect(reverse("collection_detail", kwargs={"slug": favourite.id}))


@login_required
@require_POST
def remove_follower(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        if _is_ajax(request):
            return JsonResponse({"error": "Cannot remove yourself"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    Follower.objects.filter(author=request.user, follower=target).delete()
    CloseFriend.objects.filter(owner=request.user, friend=target).delete()
    if _is_ajax(request):
        return JsonResponse({"status": "removed", "follower": target.username})
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))


@login_required
@require_POST
def remove_following(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        if _is_ajax(request):
            return JsonResponse({"error": "Cannot unfollow yourself"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    Follower.objects.filter(follower=request.user, author=target).delete()
    if _is_ajax(request):
        return JsonResponse({"status": "removed", "following": target.username})
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))


@login_required
@require_POST
def add_close_friend(request, username):
    friend = get_object_or_404(User, username=username)
    if friend == request.user:
        if _is_ajax(request):
            return JsonResponse({"error": "Cannot add yourself"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    if not Follower.objects.filter(author=request.user, follower=friend).exists():
        if _is_ajax(request):
            return JsonResponse({"error": "Must follow user first"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    CloseFriend.objects.get_or_create(owner=request.user, friend=friend)
    if _is_ajax(request):
        return JsonResponse({"status": "added", "friend": friend.username})
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))


@login_required
@require_POST
def remove_close_friend(request, username):
    friend = get_object_or_404(User, username=username)
    if friend == request.user:
        if _is_ajax(request):
            return JsonResponse({"error": "Cannot remove yourself"}, status=400)
        return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
    CloseFriend.objects.filter(owner=request.user, friend=friend).delete()
    if _is_ajax(request):
        return JsonResponse({"status": "removed", "friend": friend.username})
    return redirect(request.META.get("HTTP_REFERER") or reverse("profile"))
